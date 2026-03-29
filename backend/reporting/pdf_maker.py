from fpdf import FPDF
from datetime import datetime
import re

class ForensicReport(FPDF):
    def _clean_text(self, text):
        """
        Strips non-Latin1 characters that cause FPDF to crash when using standard fonts.
        """
        if not text: return ""
        # Keep basic Latin-1, strip everything else including emojis
        return re.sub(r'[^\x00-\xff]', '', str(text))

    def header(self):
        # Header layout
        self.set_font('Courier', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'ANTIGRAVITY // FORENSIC LEDGER', align='L', ln=0)
        self.cell(0, 10, 'CONFIDENTIAL', align='R', ln=1)
        self.line(10, 20, 200, 20)
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, title, ln=1, align='L')
        self.ln(2)

    def verdict_box(self, is_vulnerable, score):
        self.ln(5)
        self.set_font('Helvetica', 'B', 20)
        if is_vulnerable:
            self.set_fill_color(255, 235, 235) # Light Red Background
            self.set_text_color(200, 0, 0)     # Red Text
            self.cell(0, 20, f"CRITICAL VULNERABILITY DETECTED", align='C', fill=True, ln=1)
            self.set_font('Courier', 'B', 12)
            self.cell(0, 10, f"SEVERITY: HIGH ({score})", align='C', ln=1)
        else:
            self.set_fill_color(235, 255, 235) # Light Green Background
            self.set_text_color(0, 150, 0)     # Green Text
            self.cell(0, 20, "SYSTEM SECURE", align='C', fill=True, ln=1)
            self.set_font('Courier', 'B', 12)
            self.cell(0, 10, f"SCORE: {score}", align='C', ln=1)
        self.ln(10)

    def metadata_table(self, job_data):
        self.set_font('Courier', '', 10)
        self.set_text_color(0, 0, 0)
        
        # Handle both dict-based job_data and TaskTarget-based job_data
        target_url = job_data.get('target', 'N/A')
        if isinstance(target_url, dict):
            target_url = target_url.get('url', 'N/A')
            
        data = [
            ("Job ID", job_data.get('id', 'N/A')),
            ("Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")),
            ("Operator", "ZERO-DAY"),
            ("Target URL", target_url),
            ("Method", job_data.get('method', 'POST')),
            ("Payload Hash", "SHA-256 (Partial) " + str(hash(job_data.get('body', '')))[:16])
        ]
        
        for key, val in data:
            self.set_font('Courier', 'B', 10)
            self.cell(50, 8, key, 1)
            self.set_font('Courier', '', 10)
            # Use sanitizer for values
            self.cell(0, 8, self._clean_text(str(val)), 1, 1)
        self.ln(10)

    def evidence_table(self, results):
        # Table Header
        self.set_font('Courier', 'B', 10)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(50, 50, 50) # Dark Grey Header
        
        self.cell(20, 8, "SOCKET ID", 1, 0, 'C', True)
        self.cell(40, 8, "HTTP STATUS", 1, 0, 'C', True)
        self.cell(30, 8, "TYPE", 1, 0, 'C', True)
        self.cell(50, 8, "VERDICT", 1, 1, 'C', True)

        # Table Body
        self.set_font('Courier', '', 8)
        self.set_text_color(0, 0, 0)
        
        for res in results:
            # Check for Data Leak
            leaks = res.get('data_leak', [])
            leak_text = "Standard"
            is_leak = False
            
            if leaks and isinstance(leaks, list):
                leak_text = "LEAK: " + ",".join([l.split(':')[0] for l in leaks])[:15]
                is_leak = True
            
            if res.get('verdict') == "POTENTIAL_IDOR":
                leak_text = "IDOR"
                
            status_code = str(res.get('status', 'Unknown')).split(' ')[0]
            
            # Simple Verdict Logic
            if status_code.startswith('2') or is_leak or res.get('verdict') in ["POTENTIAL_IDOR", "CRITICAL_LEAK"]:
                self.set_font('Courier', 'B', 8)
                self.set_text_color(200, 0, 0) # Red for Hits
                verdict = "VULNERABLE"
            else:
                self.set_font('Courier', '', 8)
                self.set_text_color(100, 100, 100) # Grey for Misses
                verdict = "BLOCKED"

            self.cell(20, 8, f"#{res.get('socket_id', res.get('variant_id', '?'))}", 1, 0, 'C')
            status_text = str(res.get('status', 'Unknown'))
            if len(status_text) > 12:
                status_text = status_text[:10] + ".."
            self.cell(40, 8, status_text, 1, 0, 'C')
            
            # Use OFFSET column for TYPE/LEAK info now
            self.cell(30, 8, leak_text, 1, 0, 'C') 
            self.cell(50, 8, verdict, 1, 1, 'C')

    def add_forensic_truth_kernel_section(self, ai_text: str):
        """
        Parses and renders the Antigravity V12 Forensic Truth Kernel block.
        """
        sections = {
            'TITLE': r'::TITLE_START::(.*?)::TITLE_END::',
            'EXEC': r'::EXEC_SUMMARY_START::(.*?)::EXEC_SUMMARY_END::',
            'TECH': r'::TECH_DETAILS_START::(.*?)::TECH_DETAILS_END::',
            'FIX': r'::REMEDIATION_START::(.*?)::REMEDIATION_END::'
        }

        # 1. Title (Font 24, Bold)
        title_match = re.search(sections['TITLE'], ai_text, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            self.add_page()
            self.set_font('Helvetica', 'B', 24)
            self.set_text_color(0, 0, 0)
            self.multi_cell(0, 15, title, align='L')
            self.ln(5)

        # 2. Executive Points (Font 14, Bullets)
        exec_match = re.search(sections['EXEC'], ai_text, re.DOTALL)
        if exec_match:
            self.set_font('Helvetica', 'B', 16)
            self.cell(0, 10, "EXECUTIVE SUMMARY", ln=1)
            self.ln(2)
            points = exec_match.group(1).strip().split('\n')
            self.set_font('Helvetica', '', 14)
            for p in points:
                if p.strip():
                    self.multi_cell(0, 8, f" {p.strip()}")
            self.ln(5)

        # 3. Technical Deep Dive (Font 12, Bullets)
        tech_match = re.search(sections['TECH'], ai_text, re.DOTALL)
        if tech_match:
            self.set_font('Helvetica', 'B', 14)
            self.cell(0, 10, "TECHNICAL FORENSICS", ln=1)
            self.ln(2)
            details = tech_match.group(1).strip().split('\n')
            self.set_font('Helvetica', '', 12)
            for d in details:
                if d.strip():
                    self.multi_cell(0, 7, f" {d.strip()}")
            self.ln(5)

        # 4. Remediation (Font 12, Mixed)
        fix_match = re.search(sections['FIX'], ai_text, re.DOTALL)
        if fix_match:
            self.set_font('Helvetica', 'B', 14)
            self.cell(0, 10, "STRICT REMEDIATION PLAN", ln=1)
            self.ln(2)
            steps = fix_match.group(1).strip().split('\n')
            self.set_font('Helvetica', '', 12)
            for s in steps:
                if s.strip():
                    self.multi_cell(0, 7, f" {s.strip()}")
            self.ln(5)

    # ... (Previous generate method remains for backward compatibility or individual logic)
    def generate(self, job_data, results, score, vector, gemini_key=None):
        self.add_page()
        # 1. Executive Summary / Verdict
        self.chapter_title("1. THE VERDICT")
        is_vulnerable = score >= 7.0
        self.verdict_box(is_vulnerable, score)
        self.cell(0, 5, f"Vector: {vector}", ln=1, align='C')
        self.ln(5)

        # AI-Powered Executive Summary
        self.set_font('Courier', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, "EXECUTIVE SUMMARY (AI ANALYSIS)", ln=1)
        
        summary = None
        try:
            from backend.ai.cortex import CortexEngine, get_cortex_engine
            cortex = get_cortex_engine()
            target = job_data.get('target', 'Unknown')
            success_count = sum(1 for r in results if isinstance(r, dict) and str(r.get('status', '')).startswith('2'))
            summary = cortex.generate_executive_brief(target, success_count, len(results), "0.0")
        except Exception as e:
            print(f"AI Generation Failed: {e}")

        if not summary:
            # Fallback
            if is_vulnerable:
                summary = ("The target endpoint failed to handle concurrent requests. "
                           "The application allowed multiple simultaneous requests to bypass business logic checks.")
            else:
                summary = ("No race condition vulnerabilities were detected. "
                           "The Gatekeeper engine synchronized parallel requests ensuring execution within the race window.")
        
        self.set_font('Helvetica', '', 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, summary)
        self.ln(10)

        # 2. Metadata
        self.chapter_title("2. SCAN METADATA")
        self.metadata_table(job_data)
        
        # 3. Evidence
        self.add_page()
        self.chapter_title("3. ANOMALY LOG (EVIDENCE)")
        self.evidence_table(results)
        
        # 4. AI Payload Analysis
        self.add_page()
        self.chapter_title("4. PAYLOAD STRATEGY & AI ANALYSIS")
        self.set_font('Courier', '', 9)
        self.set_text_color(0, 0, 0)

        # Initialize Cortex if key available
        cortex = None
        try:
            from backend.ai.cortex import CortexEngine, get_cortex_engine
            cortex = get_cortex_engine()
        except Exception:pass

        # Try to detect if 'results' is the new variant list or old socket list
        # New structure has 'variant' key
        is_variant_list = len(results) > 0 and 'variant' in results[0]

        if is_variant_list:
            for i, res in enumerate(results):
                variant = res.get('variant', f'Variant #{i+1}')
                payload = res.get('payload', '{}')
                verdict = res.get('verdict', 'Unknown')
                
                # Visual Separator
                self.set_draw_color(200, 200, 200)
                self.line(10, self.get_y(), 200, self.get_y())
                self.ln(2)

                # Variant Header
                self.set_font('Courier', 'B', 10)
                self.cell(0, 5, f"{variant} [{verdict}]", ln=1)
                
                # Payload Dump
                self.set_font('Courier', '', 8)
                self.set_text_color(50, 50, 50)
                self.multi_cell(0, 4, f"Payload: {payload[:300] + '...' if len(payload) > 300 else payload}")
                
                # AI Analysis
                self.ln(2)
                self.set_font('Helvetica', 'I', 9)
                self.set_text_color(0, 0, 100) # Dark Blue for AI
                
                analysis = "AI Analysis Pending..."
                if cortex:
                    analysis = cortex.analyze_payload_variant(variant, payload, verdict)
                else:
                    # Fallback to Neural Core
                    try:
                        from backend.ai.cortex import CortexEngine, get_cortex_engine
                        hybrid = get_cortex_engine()
                        vuln_data = {
                            "target": job_data.get('target'),
                            "payload": payload,
                            "verdict": verdict,
                            "status": res.get('status'),
                            "variant": variant
                        }
                        analysis = hybrid.generate_forensic_report_block(vuln_data)
                        if "::TITLE_START::" in analysis:
                            self.add_forensic_truth_kernel_section(analysis)
                            continue # Skip the legacy small box if V12 succeeds
                    except Exception as e:
                        analysis = f"V12 Upgrade Failed: {e}"
                
                self.multi_cell(0, 5, f"AI Insight: {analysis}")
                self.ln(5)
                self.set_text_color(0, 0, 0)
        else:
            self.cell(0, 10, "Detail-level variant analysis unavailable for this scan type.", ln=1)

        # 5. Raw Dump (Legacy/Global)
        self.ln(10)
        self.chapter_title("5. RAW PAYLOAD (Initial Config)")
        self.set_font('Courier', '', 8)
        self.set_text_color(0, 0, 0)
        
        url_text = f"URL: {job_data.get('target', '')}"
        if len(url_text) > 80: url_text = url_text[:80] + "..."
        self.cell(0, 5, url_text, ln=1)
        
        body_text = f"Body: {job_data.get('body', '')}"
        if len(body_text) > 80: body_text = body_text[:80] + "..."
        self.cell(0, 5, body_text, ln=1)

    def generate_consolidated(self, scans_list, gemini_key=None):
        """
        Generates a Multi-Chapter Consolidated Report.
        scans_list: List of dicts {'job_data': ..., 'results': ..., 'score': ..., 'vector': ...}
        """
        # Cover Page
        self.add_page()
        self.set_font('Courier', 'B', 24)
        self.cell(0, 40, "CONSOLIDATED FORENSIC REPORT", align='C', ln=1)
        self.set_font('Courier', '', 12)
        self.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align='C', ln=1)
        self.cell(0, 10, f"Total Targets: {len(scans_list)}", align='C', ln=1)
        self.ln(20)

        # Global Summary Table
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, "MISSION SUMMARY", ln=1)
        self.set_font('Courier', 'B', 10)
        self.set_fill_color(240, 240, 240)
        self.cell(10, 10, "#", 1, 0, 'C', True)
        self.cell(100, 10, "TARGET", 1, 0, 'L', True)
        self.cell(40, 10, "STATUS", 1, 0, 'C', True)
        self.cell(30, 10, "SCORE", 1, 1, 'C', True)
        
        self.set_font('Courier', '', 10)
        total_vulns = 0
        for i, scan in enumerate(scans_list):
            target = scan['job_data'].get('target', 'Unknown')
            if len(target) > 45: target = target[:42] + "..."
            score = scan['score']
            is_vuln = score >= 7.0
            if is_vuln: total_vulns += 1
            
            self.cell(10, 10, str(i+1), 1, 0, 'C')
            self.cell(100, 10, target, 1, 0, 'L')
            
            if is_vuln:
                self.set_text_color(200, 0, 0)
                self.cell(40, 10, "VULNERABLE", 1, 0, 'C')
            else:
                self.set_text_color(0, 150, 0)
                self.cell(40, 10, "SECURE", 1, 0, 'C')
            
            self.set_text_color(0, 0, 0)
            self.cell(30, 10, str(score), 1, 1, 'C')
        
        self.ln(10)
        self.set_font('Helvetica', 'I', 10)
        self.cell(0, 10, f"Total Critical Vulnerabilities Detected: {total_vulns}", ln=1)
        
        # Individual Chapters
        for i, scan in enumerate(scans_list):
            # Page Break for each new target
            self.add_page()
            
            # Sub-Header
            self.set_font('Courier', 'B', 16)
            self.set_text_color(100, 100, 100)
            target_title = scan['job_data'].get('target', 'Unknown')
            self.cell(0, 10, f"TARGET #{i+1}: {target_title}", ln=1)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(10)
            
            # Recycle existing layout logic by calling internal helpers manually?
            # Or just copy-paste streamlined version. Let's use streamlined version to fit in memory.
            
            # Verdict
            self.chapter_title("VERDICT ANALYSIS")
            is_vulnerable = scan['score'] >= 7.0
            self.verdict_box(is_vulnerable, scan['score'])
            
            # AI Summary (Per Target)
            self.ln(5)
            self.set_font('Courier', 'B', 12)
            self.set_text_color(0, 0, 0)
            self.cell(0, 10, "AI INSIGHTS", ln=1)
            
            summary = None
            try:
                from backend.ai.cortex import CortexEngine, get_cortex_engine
                cortex = get_cortex_engine()
                success_count = sum(1 for r in scan['results'] if isinstance(r, dict) and str(r.get('status', '')).startswith('2'))
                summary = cortex.generate_executive_brief(target_title, success_count, len(scan['results']), "0.0")
            except Exception:pass
            
            if not summary:
                 summary = "AI Analysis unavailable or skipped for batch processing."

            self.set_font('Helvetica', '', 10)
            self.multi_cell(0, 6, summary)
            self.ln(10)
            
            # Evidence (Truncated for batch to save pages)
            self.chapter_title("EVIDENCE (Sample)")
            self.evidence_table(scan['results'][:20]) # Limit to top 20 rows per target
            if len(scan['results']) > 20:
                self.cell(0, 10, f"... and {len(scan['results']) - 20} more records omitted for brevity ...", ln=1, align='C')
