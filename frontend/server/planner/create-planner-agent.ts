import { createPlannerTools } from '@/server/planner/tools';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { ToolLoopAgent, InferAgentUIMessage } from 'ai';
import type { PPTPlan } from '@/features/projects/types';
import { buildSystemPrompt } from '@/server/planner/prompt';
import type { TemplateId } from '@/shared/template-config';

const kimiClient = createOpenAICompatible({
  name: 'kimi',
  baseURL: process.env.OPENAI_BASE_URL ?? 'https://api.moonshot.cn/v1',
  apiKey: process.env.OPENAI_API_KEY ?? '',
});

interface PlannerOptions {
  pptPlan?: PPTPlan;
  pageCount?: string;
  audience?: string;
  style?: string;
  templateId?: TemplateId;
}

export const PlannerAgent = new ToolLoopAgent({
  model: kimiClient(process.env.OPENAI_MODEL ?? 'kimi-k2.5'),
  instructions: buildSystemPrompt(),
  tools: createPlannerTools('__default__'),
});

export type PlannerAgentUIMessage = InferAgentUIMessage<typeof PlannerAgent>;

export function createPlannerAgent(chatId: string, options?: PlannerOptions) {
  return new ToolLoopAgent({
    model: kimiClient(process.env.OPENAI_MODEL ?? 'kimi-k2.5'),
    instructions: buildSystemPrompt(options),
    tools: createPlannerTools(chatId, options?.templateId),
    experimental_context: {
      pptPlan: options?.pptPlan,
    },
  });
}
