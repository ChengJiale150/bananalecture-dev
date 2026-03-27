import type { PPTPlan } from '@/features/projects/types';
import { STYLE_CONFIG } from '@/server/planner/style-config';

interface PlannerOptions {
  pptPlan?: PPTPlan;
  pageCount?: string;
  audience?: string;
  style?: string;
}

const STANDARD_STRUCTURE = `
1. **封面页 (cover)**
   - 标题：设计一个既包含核心知识点又充满趣味、能引发好奇心的标题
   - 描述：用一两句简短有力的话语介绍本课主题，设置悬念或展示学习价值
   - 画面描述 (content)：哆啦A梦和大雄的精美插画，构图饱满，色彩鲜明，标题文字 "标题内容" 需醒目地融入画面中，营造出开启探险或新奇发现的氛围

2. **引入页 (introduction)**
   - 标题：从生活场景或大雄的烦恼切入
   - 描述：构建一个具体的、学生易产生共鸣的困难场景，或者哆啦A梦拿出一个神奇道具引发大雄好奇的时刻。通过冲突或好奇心自然引出本课要解决的核心问题
   - 画面描述 (content)：大雄面对困难时夸张的苦恼表情，或者哆啦A梦神秘地从口袋拿出道具的瞬间。背景需交代清楚场景（如房间、学校、空地），通过表情和肢体语言以此突出戏剧张力

3. **正文页 (content)** - 可以有多页
   - 标题：提炼当前讲解步骤的核心概念
   - 描述：采用“提出概念 -> 道具/比喻解释 -> 实际应用”的逻辑。哆啦A梦通过道具或生动的比喻将抽象知识具体化，大雄通过提问或尝试来通过反馈加深理解。确保对话生动有趣，避免枯燥说教
   - 画面描述 (content)：生动的教学互动场景。可以是哆啦A梦在用未来黑板演示，或者是两人进入道具创造的虚拟空间体验知识。关键知识点或公式应以“板书”或“全息投影”的形式清晰呈现在画面中，与人物互动

4. **总结页 (summary)**
   - 标题：本次冒险/课程的收获盘点
   - 描述：将零散的知识点串联成清晰的逻辑链条或记忆口诀。通过大雄的恍然大悟或成功应用来展示学习成果
   - 画面描述 (content)：一张清晰的知识地图、思维导图或大雄的笔记特写。哆啦A梦指着重点进行最后的强调，画面整洁有序，视觉重心集中在知识总结上

5. **结束页 (ending)**
   - 标题：富有激励性的结束语
   - 描述：肯定学习者的进步，鼓励将所学应用到生活中，或预告下一次有趣的探索。营造温馨、成就感满满的氛围
   - 画面描述 (content)：哆啦A梦和大雄向屏幕前的观众开心挥手或竖起大拇指，背景可以是夕阳下的空地或温馨的房间，传递出陪伴与成长的温暖感
`;

export function buildSystemPrompt(options?: PlannerOptions) {
  const { pptPlan: existingPlan, pageCount, audience, style = 'multi_panel' } = options || {};
  const currentStyle = STYLE_CONFIG[style] || STYLE_CONFIG.multi_panel;

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

    prompt += '\n请根据用户的新需求，修改或完善这个规划。如果用户没有明确要求修改，请保留现有规划并给出回应。\n';
  } else {
    prompt += `\n现在，根据用户的输入，创建一个精彩的${currentStyle.name}教学漫画PPT规划吧！\n`;
  }

  return prompt;
}
