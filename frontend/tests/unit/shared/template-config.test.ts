import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_TEMPLATE_ID,
  TEMPLATE_REGISTRY,
  getDialogueRoles,
  getSlideStructure,
  getStyleForTemplate,
  getTemplateName,
  getToolDescription,
} from '@/shared/template-config';

const UNKNOWN_TEMPLATE_ID = 'not-a-template';

test('getTemplateName returns the configured name and falls back for unknown ids', () => {
  assert.equal(getTemplateName('doraemon'), TEMPLATE_REGISTRY.doraemon.name);
  assert.equal(getTemplateName('xiyouji'), TEMPLATE_REGISTRY.xiyouji.name);
  assert.equal(getTemplateName(UNKNOWN_TEMPLATE_ID), TEMPLATE_REGISTRY[DEFAULT_TEMPLATE_ID].name);
});

test('getDialogueRoles returns the configured roles and falls back for unknown ids', () => {
  assert.deepEqual(getDialogueRoles('xiyouji'), TEMPLATE_REGISTRY.xiyouji.roles);
  assert.deepEqual(
    getDialogueRoles(UNKNOWN_TEMPLATE_ID),
    TEMPLATE_REGISTRY[DEFAULT_TEMPLATE_ID].roles
  );
});

test('getSlideStructure returns the configured structure and falls back for unknown ids', () => {
  assert.equal(getSlideStructure('doraemon'), TEMPLATE_REGISTRY.doraemon.slideStructure);
  assert.equal(
    getSlideStructure(UNKNOWN_TEMPLATE_ID),
    TEMPLATE_REGISTRY[DEFAULT_TEMPLATE_ID].slideStructure
  );
});

test('getToolDescription returns the configured description and falls back for unknown ids', () => {
  assert.equal(getToolDescription('xiyouji'), TEMPLATE_REGISTRY.xiyouji.toolDescription);
  assert.equal(
    getToolDescription(UNKNOWN_TEMPLATE_ID),
    TEMPLATE_REGISTRY[DEFAULT_TEMPLATE_ID].toolDescription
  );
});

test('getStyleForTemplate resolves styles and falls back for unknown template or style', () => {
  assert.equal(
    getStyleForTemplate('doraemon', 'flat'),
    TEMPLATE_REGISTRY.doraemon.styles.flat
  );
  assert.equal(
    getStyleForTemplate(UNKNOWN_TEMPLATE_ID, 'flat'),
    TEMPLATE_REGISTRY[DEFAULT_TEMPLATE_ID].styles.flat
  );
  assert.equal(
    getStyleForTemplate('doraemon', 'not-a-style'),
    TEMPLATE_REGISTRY.doraemon.styles.multi_panel
  );
});
