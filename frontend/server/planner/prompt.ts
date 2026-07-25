import type { PPTPlan } from '@/features/projects/types';
import {
  DEFAULT_TEMPLATE_ID,
  getSlideStructure,
  getStyleForTemplate,
  type TemplateId,
} from '@/shared/template-config';

interface PlannerOptions {
  pptPlan?: PPTPlan;
  pageCount?: string;
  audience?: string;
  style?: string;
  templateId?: TemplateId;
}

export function buildSystemPrompt(options?: PlannerOptions) {
  const { pptPlan: existingPlan, pageCount, audience, style = 'multi_panel', templateId = DEFAULT_TEMPLATE_ID } = options || {};
  const currentStyle = getStyleForTemplate(templateId, style);
  const STANDARD_STRUCTURE = getSlideStructure(templateId);

  let prompt = `
你是一位出色的${currentStyle.role}！你的任务是根据用户的教学内容，创作出生动有趣的${currentStyle.name}风格教学漫画PPT规划。

# 任务
收到用户的教学内容后，你需要：
1. 深入理解教学内容
2. 使用 \`create_ppt_plan\` 工具创建一个完整的PPT规划
3. **特别注意**：每个页面的 \`content\` 字段必须是详细的图片画面描述提示词。

## 图片描述提示词规范 (Content 字段)
请严格遵循以下标准编写 \`content\` 字段：

1. **用自然语言清晰描述画面**
   - 建议用简洁连贯的自然语言写明 **主体 + 行为 + 环境**
   - 若对画面美学有要求，可用自然语言或短语补充 **风格、色彩、光影、构图** 等美学元素
   - **风格强调**：必须在每张图片的描述中明确包含以下风格关键词：**${currentStyle.visualPrompt}**

2. **提高文本渲染准确度**
   - 建议将要生成的 **文字内容** 放在 **双引号** 中
   - **文本强调**：必须在每张图片的描述中明确包含以下文本关键词：**要求所有的对话使用中文而不是日文**

## 标准PPT结构（必须包含）
${STANDARD_STRUCTURE}

## 创作风格要求
- **生动有趣**：充满童趣和幽默感
- **风格统一**：确保所有页面都符合 **${currentStyle.name}** 的风格设定
- **画面感强**：\`content\` 字段必须是画面描述，不是对话脚本
`;

  if (pageCount) {
    let pageCountText = pageCount;
    if (pageCount === '15+') pageCountText = '15页以上';
    else if (pageCount === '5-10') pageCountText = '5-10页';
    else if (pageCount === '10-15') pageCountText = '10-15页';
    prompt += `\n- **页数规划**：请规划 ${pageCountText} 的内容。\n`;
  }

  if (audience) {
    let audienceText = audience;
    if (audience === 'beginner') audienceText = '初学者（注重基础，简单易懂）';
    else if (audience === 'intermediate') audienceText = '有基础（适当深入，注重实践）';
    else if (audience === 'expert') audienceText = '精通（专业深度，探讨前沿）';
    prompt += `\n- **目标受众**：${audienceText}。\n`;
  }

  prompt += `\n- **风格要求**：${currentStyle.visualPrompt}。\n`;

  if (existingPlan?.slides?.length) {
    prompt += '\n## 已有的PPT规划\n用户已经有一个PPT规划，请参考并基于此进行修改、完善或扩展：\n';

    existingPlan.slides.forEach((slide, index) => {
      prompt += `
### 第 ${index + 1} 页 - ${slide.type}
**标题**: ${slide.title}
**描述**: ${slide.description}
${slide.content ? `**画面描述**: ${slide.content}` : ''}
`;
    });

    prompt +=
      '\n请根据用户的新需求，修改或完善这个规划。如果用户没有明确要求修改，请保留现有规划并给出回应。\n';
  } else {
    prompt += `\n现在，根据用户的输入，创建一个精彩的${currentStyle.name}教学漫画PPT规划吧！\n`;
  }

  return prompt;
}
