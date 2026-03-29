#!/bin/bash
# actions-full.sh — API advanced action scenarios.

GROUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${GROUP_DIR}/../helpers/api.sh"
source "${GROUP_DIR}/../helpers/api-snapshot.sh"
source "${GROUP_DIR}/../helpers/api-actions.sh"

# ─────────────────────────────────────────────────────────────────
start_test "HTTP: dblclick by ref"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
sleep 1

pt_get /snapshot
REF=$(echo "$RESULT" | jq -r '[.nodes[] | select(.name == "Increment")][0].ref // empty')

pt_post /action -d "{\"kind\":\"dblclick\",\"ref\":\"$REF\"}"
assert_ok "dblclick by ref"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "HTTP: dblclick by CSS selector"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
sleep 1

pt_post /action -d "{\"kind\":\"dblclick\",\"selector\":\"#increment\"}"
assert_ok "dblclick by selector"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "HTTP: dblclick by coordinates"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
sleep 1

pt_post /action -d "{\"kind\":\"dblclick\",\"x\":100,\"y\":100,\"hasXY\":true}"
assert_ok "dblclick by coordinates"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "CLI: pinchtab dblclick <ref>"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
sleep 1

pt_get /snapshot
REF=$(echo "$RESULT" | jq -r '[.nodes[] | select(.name == "Increment")][0].ref // empty')

run_cli dblclick "$REF"
assert_ok "CLI dblclick by ref"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "CLI: pinchtab dblclick --css <selector>"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
sleep 1

run_cli dblclick --css "#increment"
assert_ok "CLI dblclick by selector"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "CLI: pinchtab dblclick --tab <id>"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/buttons.html\",\"newTab\":true}"
assert_ok "navigate for new tab"
TAB_ID=$(echo "$RESULT" | jq -r '.tabId')

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
sleep 1

pt_get /snapshot
REF=$(echo "$RESULT" | jq -r '[.nodes[] | select(.name == "Increment")][0].ref // empty')

run_cli dblclick "$REF" --tab "$TAB_ID"
assert_ok "CLI dblclick with --tab flag"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "HTTP: dblclick validation - missing ref/selector/coordinates"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"

pt_post /action -d "{\"kind\":\"dblclick\"}"
assert_error "dblclick without parameters should fail"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "humanClick: click input by ref"

navigate_fixture "human-type.html"
fresh_snapshot

require_ref "textbox" "Email" EMAIL_REF && \
  action_human_click "$EMAIL_REF"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "humanType: type into input by ref"

fresh_snapshot
require_ref "textbox" "Email" EMAIL_REF && {
  action_human_type "$EMAIL_REF" "test@example.com"

  fresh_snapshot
  assert_value "textbox" "Email" "test@example.com"
}

end_test

# ─────────────────────────────────────────────────────────────────
start_test "humanType: type into second input by ref"

fresh_snapshot
require_ref "textbox" "Name" NAME_REF && {
  action_human_type "$NAME_REF" "John Doe"

  fresh_snapshot
  assert_value "textbox" "Name" "John Doe"
}

end_test

# ─────────────────────────────────────────────────────────────────
start_test "humanType: type with CSS selector"

action_human_type_selector "#name" " Jr."

end_test

# Regression test for GitHub issue #236: press action was typing key names
# as literal text instead of dispatching keyboard events.

# Use permissive instance (needs evaluate enabled)
E2E_SERVER="http://pinchtab:9999"

# ─────────────────────────────────────────────────────────────────
start_test "press Enter: does not type 'Enter' as text"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/form.html\"}"
sleep 1

pt_post /action -d '{"kind":"type","selector":"#username","text":"testuser"}'
assert_ok "type into username"

pt_post /action -d '{"kind":"press","key":"Enter"}'
assert_ok "press Enter"

assert_input_not_contains "#username" "Enter" "Enter key should dispatch event, not type text (bug #236)"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "press Tab: does not type 'Tab' as text"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/form.html\"}"
sleep 1

pt_post /action -d '{"kind":"click","selector":"#username"}'
pt_post /action -d '{"kind":"type","selector":"#username","text":"hello"}'
assert_ok "type hello"

pt_post /action -d '{"kind":"press","key":"Tab"}'
assert_ok "press Tab"

assert_input_not_contains "#username" "Tab" "Tab key should dispatch event, not type text (bug #236)"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "press Escape: does not type 'Escape' as text"

pt_post /navigate -d "{\"url\":\"${FIXTURES_URL}/form.html\"}"
sleep 1

pt_post /action -d '{"kind":"type","selector":"#username","text":"world"}'
assert_ok "type world"

pt_post /action -d '{"kind":"press","key":"Escape"}'
assert_ok "press Escape"

assert_input_not_contains "#username" "Escape" "Escape key should dispatch event, not type text (bug #236)"

end_test

# Migrated from: tests/integration/actions_test.go (error cases)

pt_post /navigate "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
assert_ok "navigate"

# ─────────────────────────────────────────────────────────────────
start_test "action: unknown kind → error"

pt_post /action '{"kind":"explode","ref":"e0"}'
assert_not_ok "rejects unknown kind"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "action: missing kind → error"

pt_post /action '{"ref":"e0"}'
assert_http_status "400" "rejects missing kind"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "action: ref not found → error"

pt_post /action '{"kind":"click","ref":"e999"}'
assert_not_ok "rejects missing ref"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "action: batch operations"

pt_post /actions '{"actions":[{"kind":"click","ref":"e4"},{"kind":"click","ref":"e5"}]}'
assert_ok "batch actions"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "action: empty batch → error"

pt_post /actions '{"actions":[]}'
assert_not_ok "rejects empty batch"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "action: nonexistent tabId → error"

pt_post /action '{"kind":"click","ref":"e0","tabId":"nonexistent_xyz_999"}'
assert_not_ok "rejects bad tab"

end_test

# ─────────────────────────────────────────────────────────────────
# POST /dialog — JavaScript dialog handling
# ─────────────────────────────────────────────────────────────────

start_test "POST /dialog: invalid JSON"

pt_post_raw /dialog "not json"
assert_http_status "400" "rejects invalid JSON"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "POST /dialog: missing action"

pt_post /dialog '{}'
assert_http_status "400" "rejects missing action"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "POST /dialog: invalid action"

pt_post /dialog '{"action":"invalid"}'
assert_http_status "400" "rejects invalid action"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "POST /dialog: no pending dialog"

# Navigate to a page that has no dialog
pt_post /navigate "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
assert_ok "navigate"
sleep 0.5

# Try to accept a dialog when none is pending
pt_post /dialog '{"action":"accept"}'
# Should fail because no dialog is pending
assert_http_status "400" "rejects when no dialog pending"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "POST /dialog: accept action format"

# This test verifies the request format is accepted
# Note: Actually triggering and accepting a dialog requires JS execution
# which may not be enabled in all test configurations

pt_post /navigate "{\"url\":\"${FIXTURES_URL}/buttons.html\"}"
TAB_ID=$(get_tab_id)

# Try accept with tabId - should fail gracefully if no dialog
pt_post /dialog "{\"action\":\"accept\",\"tabId\":\"${TAB_ID}\"}"
# Expected: 400 (no pending dialog) - this confirms the endpoint works
assert_http_status "400" "accept request format valid (no pending dialog)"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "POST /dialog: dismiss action format"

# Try dismiss with text - should fail gracefully if no dialog
pt_post /dialog "{\"action\":\"dismiss\",\"tabId\":\"${TAB_ID}\"}"
assert_http_status "400" "dismiss request format valid (no pending dialog)"

end_test

# ─────────────────────────────────────────────────────────────────
start_test "POST /dialog: accept with prompt text"

# Test the prompt text parameter format
pt_post /dialog "{\"action\":\"accept\",\"tabId\":\"${TAB_ID}\",\"text\":\"my response\"}"
# Should fail because no dialog is pending, but format is valid
assert_http_status "400" "accept with text format valid (no pending dialog)"

end_test
