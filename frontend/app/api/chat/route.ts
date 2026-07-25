import { createPlannerAgent } from '@/server/planner/create-planner-agent';
import { DEFAULT_TEMPLATE_ID, TEMPLATE_REGISTRY, type TemplateId } from '@/shared/template-config';
import { createAgentUIStreamResponse } from 'ai';

export async function POST(request: Request) {
  const url = new URL(request.url);
  const payload = await request.json().catch(() => ({}));
  const messages = payload?.messages ?? [];
  const idFromBody = payload?.id;
  const pptPlan = payload?.pptPlan;
  const pageCount = payload?.pageCount;
  const audience = payload?.audience;
  const style = payload?.style;
  const template: TemplateId =
    typeof payload?.template === 'string' && Object.hasOwn(TEMPLATE_REGISTRY, payload.template)
      ? (payload.template as TemplateId)
      : DEFAULT_TEMPLATE_ID;
  const idFromQuery = url.searchParams.get('id');
  const idFromHeader = request.headers.get('x-chat-id');
  const chatId = (idFromBody || idFromQuery || idFromHeader) as string | null;

  if (!chatId) {
    return Response.json({ error: 'Missing chat id' }, { status: 400 });
  }

  return createAgentUIStreamResponse({
    agent: createPlannerAgent(chatId, {
      pptPlan,
      pageCount,
      audience,
      style,
      templateId: template,
    }),
    uiMessages: messages,
  });
}
