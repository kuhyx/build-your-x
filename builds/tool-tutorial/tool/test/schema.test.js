// Dependency-free on purpose: the repo gate runs `npm test` here without an
// install step, so this checks the one data file the tool ships.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const schema = JSON.parse(
	readFileSync(new URL('../src/config/schema.json', import.meta.url), 'utf8'),
);

test('config schema declares a numeric port', () => {
	assert.equal(schema.properties.port.type, 'number');
});
