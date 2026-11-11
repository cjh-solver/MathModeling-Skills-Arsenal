const { test } = require('node:test');
const assert = require('node:assert/strict');
const { QuestionLabels: labels } = require('../static/ranking.js');

test('recognized question descriptions and identifiers use Chinese labels', () => {
  assert.equal(labels.text('satisfy hourly load under budget and minimize surplus generation'), '在预算约束下满足逐时负荷，最小化多余发电量');
  assert.equal(labels.text('hourly_load_kw'), '逐时负荷（kW）');
  assert.equal(labels.model('Q2-final-model'), 'Q2 最终模型');
});

test('result labels preserve exact values and leave unknown content unchanged', () => {
  assert.equal(labels.result('wind_units=16; cost_cny=94000; curtailment_kwh=5357.74888888889; unknown=4'), '风机数量=16; 成本（元）=94000; 弃电量（kWh）=5357.74888888889; unknown=4');
  assert.equal(labels.text('unknown project description'), 'unknown project description');
  assert.equal(labels.model('custom-model'), 'custom-model');
  assert.equal(labels.result(42), 42);
});
