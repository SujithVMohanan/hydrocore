'use strict';

/** Client-side chart data transform — no API calls. */

function bucketKey(date, mode) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    if (mode === 'yearly') return `${y}`;
    if (mode === 'monthly') return `${y}-${m}`;
    return `${y}-${m}-${d}`;
}

function formatBucketLabel(key, mode) {
    if (mode === 'yearly') return key;
    if (mode === 'monthly') {
        const [y, m] = key.split('-');
        return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString([], { month: 'short', year: 'numeric' });
    }
    const [y, m, d] = key.split('-');
    return new Date(Number(y), Number(m) - 1, Number(d)).toLocaleDateString([], {
        month: 'short', day: 'numeric', year: 'numeric',
    });
}

export function aggregateTimeseries(points, mode, valueAgg = 'sum') {
    if (mode === 'daily') {
        const buckets = {};
        points.forEach(pt => {
            const key = bucketKey(new Date(pt.timestamp), 'daily');
            if (!buckets[key]) {
                buckets[key] = { sum: 0, count: 0, min: pt.timestamp };
            }
            buckets[key].sum += Number(pt.value) || 0;
            buckets[key].count += 1;
        });
        return Object.keys(buckets).sort().map(key => ({
            timestamp: formatBucketLabel(key, 'daily'),
            value: valueAgg === 'avg'
                ? buckets[key].sum / buckets[key].count
                : buckets[key].sum,
            label: formatBucketLabel(key, 'daily'),
            bucketKey: key,
        }));
    }

    const buckets = {};

    points.forEach(pt => {
        const key = bucketKey(new Date(pt.timestamp), mode);
        if (!buckets[key]) {
            buckets[key] = { sum: 0, count: 0, min: pt.timestamp };
        }
        buckets[key].sum += Number(pt.value) || 0;
        buckets[key].count += 1;
        if (new Date(pt.timestamp) < new Date(buckets[key].min)) {
            buckets[key].min = pt.timestamp;
        }
    });

    return Object.keys(buckets).sort().map(key => ({
        timestamp: buckets[key].min,
        value: valueAgg === 'avg'
            ? buckets[key].sum / buckets[key].count
            : buckets[key].sum,
        label: formatBucketLabel(key, mode),
        bucketKey: key,
    }));
}

export function prepareChartData(rainfallRaw, tempRaw, eventsRaw, mode) {
    const rainAgg = aggregateTimeseries(rainfallRaw, mode, 'sum');
    const tempAgg = aggregateTimeseries(tempRaw, mode, 'avg');

    const rainForChart = rainAgg.map(r => ({
        timestamp: r.label || r.timestamp,
        value: Number(r.value.toFixed(2)),
        rawTimestamp: r.timestamp,
    }));

    const tempForChart = tempAgg.map(t => ({
        timestamp: t.label || t.timestamp,
        value: Number(t.value.toFixed(2)),
        rawTimestamp: t.timestamp,
    }));

    const eventsForChart = eventsRaw.map(ev => ({
        ...ev,
        start_timestamp: ev.start_timestamp,
        end_timestamp: ev.end_timestamp,
    }));

    return {
        rainfall: rainForChart,
        temperature: tempForChart,
        events: eventsForChart,
        mode,
    };
}
