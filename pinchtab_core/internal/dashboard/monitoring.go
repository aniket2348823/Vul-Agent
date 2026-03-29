package dashboard

import (
	"time"

	apiTypes "github.com/pinchtab/pinchtab/internal/api/types"
	"github.com/pinchtab/pinchtab/internal/bridge"
)

type MonitoringSource interface {
	List() []bridge.Instance
	AllTabs() []bridge.InstanceTab
	AllMetrics() []apiTypes.InstanceMetrics
}

type MonitoringServerMetrics struct {
	GoHeapAllocMB   float64 `json:"goHeapAllocMB"`
	GoNumGoroutine  int     `json:"goNumGoroutine"`
	RateBucketHosts int     `json:"rateBucketHosts"`
}

type MonitoringSnapshot struct {
	Timestamp     int64                      `json:"timestamp"`
	Instances     []bridge.Instance          `json:"instances"`
	Tabs          []bridge.InstanceTab       `json:"tabs"`
	Metrics       []apiTypes.InstanceMetrics `json:"metrics"`
	ServerMetrics MonitoringServerMetrics    `json:"serverMetrics"`
}

type ServerMetricsProvider func() MonitoringServerMetrics

func (d *Dashboard) SetMonitoringSource(src MonitoringSource) {
	d.monitoring = src
	if src != nil {
		d.instances = src
	}
}

func (d *Dashboard) SetServerMetricsProvider(provider ServerMetricsProvider) {
	d.serverMetrics = provider
}

func (d *Dashboard) monitoringSnapshot(includeMemory bool) MonitoringSnapshot {
	snapshot := MonitoringSnapshot{
		Timestamp: time.Now().UnixMilli(),
		Instances: []bridge.Instance{},
		Tabs:      []bridge.InstanceTab{},
		Metrics:   []apiTypes.InstanceMetrics{},
	}

	if d.monitoring != nil {
		snapshot.Instances = d.monitoring.List()
		snapshot.Tabs = d.monitoring.AllTabs()
		if includeMemory {
			snapshot.Metrics = d.monitoring.AllMetrics()
		}
	} else if d.instances != nil {
		snapshot.Instances = d.instances.List()
	}

	if d.serverMetrics != nil {
		snapshot.ServerMetrics = d.serverMetrics()
	}

	return snapshot
}
