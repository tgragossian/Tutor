// Offline desired-behavior probe; TODO deliberately records C1-R8's current failure.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

test('C1-R8: retry after an ambiguous response reuses the request ID',
  { todo: 'Retain unresolved help requests until a definitive response or item change' },
  async () => {
    const source = readFileSync(new URL('../../../src/mathtutor/web/static/practice.js',
      import.meta.url), 'utf8')
      .replace(/^import .*;\r?\n/gm, '').replace(/load\(\);\s*$/, '');
    const elements = new Map();
    const element = (id) => {
      if (!elements.has(id)) elements.set(id, {
        dataset: { sessionId: '1' }, content: 'csrf',
        addEventListener() {}, setAttribute() {}, append() {},
      });
      return elements.get(id);
    };
    let uuid = 0;
    const context = vm.createContext({
      MathfieldElement: class {}, ComputeEngine: class {},
      document: { getElementById: element, querySelector: element,
        querySelectorAll: () => [], createElement: element },
      crypto: { randomUUID: () => `uuid-${++uuid}` },
    });
    vm.runInContext(source, context);
    vm.runInContext(`
      item = { session_item_id: 1, revision: 0, help: { enabled: true } };
      globalThis.sent = [];
      helpApi = async (body) => {
        sent.push({ ...body });
        // The server may have generated and committed the hint before the response was lost.
        throw new Error('response lost');
      };
    `, context);
    await vm.runInContext("askHelp('hint')", context);
    await vm.runInContext("askHelp('hint')", context);
    assert.equal(context.sent.length, 2);
    assert.equal(context.sent[1].help_request_id, context.sent[0].help_request_id);
  });
