const jsdom = require('jsdom');
const d3 = require('../d3');
const topojson = require('../topojson');
const mapChart = require('../d3.map.districts')(d3, topojson);
const mapdata = require('../../../static/mapdata/2017/gr.json');
const data = {
  "Albula": {
    counted: true,
    municipalities: [3506,3514,3513,3521,3543,3542,3522],
    yeas_percentage: 41.8,
    nays_percentage: 58.1
  },
  "Bernina": {
    counted: true,
    municipalities: [3561,3551],
    yeas_percentage: 47.1,
    nays_percentage: 52.8
  },
  "Engiadina": {
    counted: true,
    municipalities: [3752,3847,3746,3764,3762],
    yeas_percentage: 39.0,
    nays_percentage: 60.9
  },
  "Imboden": {
    counted: true,
    municipalities: [3722,3734,3733,3732,3723,3731,3721],
    yeas_percentage: 35.9,
    nays_percentage: 64.0
  },
  "Landquart": {
    counted: true,
    municipalities: [3951,3955,3954,3952,3946,3945,3953,3947],
    yeas_percentage: 35.8,
    nays_percentage: 64.1
  },
  "Maloja": {
    counted: true,
    municipalities: [3786,3787,3789,3792,3788,3783,3781,3790,3785,3784,3791,3782],
    yeas_percentage: 48.3,
    nays_percentage: 51.6
  },
  "Moesa": {
    counted: true,
    municipalities: [3804,3831,3810,3834,3821,3835,3832,3837,3823,3805,3808,3822],
    yeas_percentage: 39.7,
    nays_percentage: 60.2
  },
  "Plessur": {
    counted: true,
    municipalities: [3941,3926,3921,3901,3911,3932],
    yeas_percentage: 34.8,
    nays_percentage: 65.1
  },
  "Pr\u00e4ttigau": {
    counted: true,
    municipalities: [3861,3862,3962,3972,3882,3881,3863,3891,3871,3851,3961],
    yeas_percentage: 39.3,
    nays_percentage: 60.6
  },
  "Surselva": {
    counted: true,
    municipalities: [3985,3988,3611,3616,3619,3575,3986,3581,3618,3981,3987,3983,3582,3672,3982,3603,3572],
    yeas_percentage: 38.1,
    nays_percentage: 61.8
  },
  "Viamala":{
      counted: true,
      municipalities: [3695,3638,3708,3670,3633,3662,3503,3712,3668,3705,3703,3691,3711,3707,3694,3681,3663,3713,3673,3637,3669,3640,3661,3701,3693],
      yeas_percentage: 32.3096339924274,
      nays_percentage:67.6903660075726
  }
};

describe('Map', () => {
  // Note that our bounding box mockup is not good enough to allow the map to
  // find the right height, the viewbox of the generated SVGs is not correct

  it('renders an empty svg with no data', () => {
    var document = jsdom.jsdom();
    var chart = mapChart();
    chart(document.body);
    expect(document.svg(d3)).toMatchSnapshot();
  });

  it('renders a svg @1', () => {
    var document = jsdom.jsdom();
    var chart = mapChart({
      width: 1,
      mapdata: mapdata,
      data: data,
      canton: 'zg'
    });

    chart(document.body);
    // require('fs').writeFile("map@1.svg", document.svg());
    expect(document.svg()).toMatchSnapshot();
    expect(chart.width()).toBe(1);
  });

  it('renders a svg @200', () => {
    var document = jsdom.jsdom();
    var chart = mapChart({
      width: 200,
      mapdata: mapdata,
      data: data,
      canton: 'zg'
    });

    chart(document.body);
    // require('fs').writeFile("map@200.svg", document.svg());
    expect(document.svg()).toMatchSnapshot();
    expect(chart.width()).toBe(200);
  });

  it('renders a svg @500', () => {
    var document = jsdom.jsdom();
    var chart = mapChart({
      width: 500,
      mapdata: mapdata,
      data: data,
      canton: 'zg'
    });

    chart(document.body);
    // require('fs').writeFile("map@500.svg", document.svg());
    expect(document.svg()).toMatchSnapshot();
    expect(chart.width()).toBe(500);
  });

  it('renders a svg @700', () => {
    var document = jsdom.jsdom();
    var chart = mapChart({
      width: 700,
      mapdata: mapdata,
      data: data,
      canton: 'zg'
    });

    chart(document.body);
    // require('fs').writeFile("map@700.svg", document.svg());
    expect(document.svg()).toMatchSnapshot();
    expect(chart.width()).toBe(700);
  });

  it('renders a svg @2000', () => {
    var document = jsdom.jsdom();
    var chart = mapChart({
      width: 2000,
      mapdata: mapdata,
      data: data,
      canton: 'zg'
    });

    chart(document.body);
    // require('fs').writeFile("map@2000.svg", document.svg());
    expect(document.svg()).toMatchSnapshot();
    expect(chart.width()).toBe(2000);
  });

  it('renders the translations', () => {
    var document = jsdom.jsdom();
    var chart = mapChart({
      width: 2000,
      mapdata: mapdata,
      data: data,
      canton: 'zg',
      yay: 'Ja',
      nay: 'Nein'
    });

    chart(document.body);
    expect(document.svg()).toMatch('Ja');
    expect(document.svg()).toMatch('Nein');
  });
});