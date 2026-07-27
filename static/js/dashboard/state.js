'use strict';

export const state = {
    rainfallChart: null,
    temperatureChart: null,
    combinedChart: null,
    chartLayoutMode: 'split',
    allEvents: [],
    rainfallTimeseries: [],
    temperatureTimeseries: [],
    rawRainfallTimeseries: [],
    rawTemperatureTimeseries: [],
    rawEvents: [],
    currentPage: 1,
    pageSize: 10,
    pendingBasinId: null,
    pendingStartDate: null,
    pendingEndDate: null,
    pendingDryGap: 6,
    startPicker: null,
    endPicker: null,
    chartViewMode: 'daily',
};

export const PAGE_SIZE = 10;
