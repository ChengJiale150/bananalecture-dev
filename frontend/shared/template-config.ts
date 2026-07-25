export type TemplateId = 'doraemon' | 'xiyouji';

export const DEFAULT_TEMPLATE_ID: TemplateId = 'doraemon';

interface TemplateSlideStructure {
  slideStructure: string;
  styles: Record<string, { name: string; role: string; description: string; visualPrompt: string }>;
  toolDescription: string;
}

export const TEMPLATE_REGISTRY: Record<string, TemplateSlideStructure & { name: string; roles: readonly string[] }> = {
  doraemon: {
    name: '哆啦A梦',
    roles: ['大雄', '哆啦A梦', '旁白', '其他男声', '其他女声', '道具'] as const,
    slideStructure: `
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
   - 描述：采用"提出概念 -> 道具/比喻解释 -> 实际应用"的逻辑。哆啦A梦通过道具或生动的比喻将抽象知识具体化，大雄通过提问或尝试来通过反馈加深理解。确保对话生动有趣，避免枯燥说教
   - 画面描述 (content)：生动的教学互动场景。可以是哆啦A梦在用未来黑板演示，或者是两人进入道具创造的虚拟空间体验知识。关键知识点或公式应以"板书"或"全息投影"的形式清晰呈现在画面中，与人物互动

4. **总结页 (summary)**
   - 标题：本次冒险/课程的收获盘点
   - 描述：将零散的知识点串联成清晰的逻辑链条或记忆口诀。通过大雄的恍然大悟或成功应用来展示学习成果
   - 画面描述 (content)：一张清晰的知识地图、思维导图或大雄的笔记特写。哆啦A梦指着重点进行最后的强调，画面整洁有序，视觉重心集中在知识总结上

5. **结束页 (ending)**
   - 标题：富有激励性的结束语
   - 描述：肯定学习者的进步，鼓励将所学应用到生活中，或预告下一次有趣的探索。营造温馨、成就感满满的氛围
   - 画面描述 (content)：哆啦A梦和大雄向屏幕前的观众开心挥手或竖起大拇指，背景可以是夕阳下的空地或温馨的房间，传递出陪伴与成长的温暖感
`,
    styles: {
      multi_panel: {
        name: '多格动漫',
        role: '多格动漫教学漫画规划师',
        description: '注重叙事节奏的多格漫画风格',
        visualPrompt:
          '哆啦A梦和大雄的多格漫画分镜风格，画面分割清晰，人物动作夸张生动，背景细节丰富，具有强烈的动态感',
      },
      colorful_comic: {
        name: '彩色漫画',
        role: '彩色漫画教学漫画规划师',
        description: '色彩丰富饱满的现代漫画风格',
        visualPrompt:
          '哆啦A梦和大雄的彩色漫画风格，色彩鲜艳丰富，高饱和度，现代彩色漫画风格，光影效果强烈，构图大胆',
      },
      flat: {
        name: '扁平插画',
        role: '扁平插画教学漫画规划师',
        description: '简约现代的扁平化设计风格',
        visualPrompt:
          '哆啦A梦和大雄的现代扁平化插画风格(Flat Illustration)，几何图形为主，色彩搭配和谐，无多余细节，抽象而富有寓意',
      },
    },
    toolDescription:
      'Create a teaching comic plan for Doraemon-style PPT slides. Create a vivid and fun educational manga plan including cover, introduction, content with Doraemon and Nobita dialogues, summary, and ending page.',
  },
  xiyouji: {
    name: '西游记',
    roles: ['悟空', '八戒', '旁白'] as const,
    slideStructure: `
1. **封面页 (cover)**
   - 标题：设计一个既包含核心知识点又充满趣味、能引发好奇心的标题
   - 描述：用一两句简短有力的话语介绍本课主题，设置悬念或展示学习价值
   - 画面描述 (content)：悟空和八戒的精美插画，中国水墨风格，构图饱满，色彩鲜明，标题文字 "标题内容" 需醒目地融入画面中，营造出开启修行或新奇发现的氛围

2. **引入页 (introduction)**
   - 标题：从生活场景或八戒的烦恼切入
   - 描述：构建一个具体的、学生易产生共鸣的困难场景，或者悟空展示一个神奇法术引发八戒好奇的时刻。通过冲突或好奇心自然引出本课要解决的核心问题
   - 画面描述 (content)：八戒面对困难时抓耳挠腮的苦恼表情，或者悟空神秘地掏出金箍棒的瞬间。背景需交代清楚场景（如山林、庙宇、云海），通过表情和肢体语言以此突出戏剧张力

3. **正文页 (content)** - 可以有多页
   - 标题：提炼当前讲解步骤的核心概念
   - 描述：采用"提出概念 -> 神通/比喻解释 -> 实际应用"的逻辑。悟空通过神通或生动的比喻将抽象知识具体化，八戒通过提问或尝试来通过反馈加深理解。确保对话生动有趣，避免枯燥说教
   - 画面描述 (content)：生动的教学互动场景。可以是悟空在用仙术演示，或者是两人进入仙境体验知识。关键知识点或公式应以"板书"或"仙术投影"的形式清晰呈现在画面中，与人物互动

4. **总结页 (summary)**
   - 标题：本次修行的收获盘点
   - 描述：将零散的知识点串联成清晰的逻辑链条或记忆口诀。通过八戒的恍然大悟或成功应用来展示学习成果
   - 画面描述 (content)：一张清晰的知识地图、悟空的仙术笔记特写。悟空指着重点进行最后的强调，画面整洁有序，视觉重心集中在知识总结上

5. **结束页 (ending)**
   - 标题：富有激励性的结束语
   - 描述：肯定学习者的进步，鼓励将所学应用到生活中，或预告下一次有趣的探索。营造温馨、成就感满满的氛围
   - 画面描述 (content)：悟空和八戒向屏幕前的观众开心挥手或竖起大拇指，背景可以是夕阳下的山林或云海仙境，传递出陪伴与成长的温暖感
`,
    styles: {
      multi_panel: {
        name: '多格动漫',
        role: '多格动漫教学漫画规划师',
        description: '注重叙事节奏的多格漫画风格',
        visualPrompt:
          '悟空和八戒的多格漫画分镜风格，画面分割清晰，人物动作夸张生动，背景细节丰富，具有强烈的动态感',
      },
      colorful_comic: {
        name: '彩色漫画',
        role: '彩色漫画教学漫画规划师',
        description: '色彩丰富饱满的现代漫画风格',
        visualPrompt:
          '悟空和八戒的彩色漫画风格，色彩鲜艳丰富，高饱和度，现代彩色漫画风格，光影效果强烈，构图大胆',
      },
      flat: {
        name: '扁平插画',
        role: '扁平插画教学漫画规划师',
        description: '简约现代的扁平化设计风格',
        visualPrompt:
          '悟空和八戒的现代扁平化插画风格(Flat Illustration)，几何图形为主，色彩搭配和谐，无多余细节，抽象而富有寓意',
      },
    },
    toolDescription:
      'Create a teaching comic plan for Journey to the West-style PPT slides. Create a vivid and fun educational manga plan including cover, introduction, content with Wukong and Bajie dialogues, summary, and ending page.',
  },
};

export function getTemplateName(templateId: string): string {
  return TEMPLATE_REGISTRY[templateId]?.name ?? TEMPLATE_REGISTRY.doraemon.name;
}

export function getDialogueRoles(templateId: string): readonly string[] {
  return TEMPLATE_REGISTRY[templateId]?.roles ?? TEMPLATE_REGISTRY.doraemon.roles;
}

export function getSlideStructure(templateId: string): string {
  return TEMPLATE_REGISTRY[templateId]?.slideStructure ?? TEMPLATE_REGISTRY.doraemon.slideStructure;
}

export function getToolDescription(templateId: string): string {
  return TEMPLATE_REGISTRY[templateId]?.toolDescription ?? TEMPLATE_REGISTRY.doraemon.toolDescription;
}

export function getStyleForTemplate(
  templateId: string,
  style: string
): { name: string; role: string; description: string; visualPrompt: string } {
  const styles = TEMPLATE_REGISTRY[templateId]?.styles ?? TEMPLATE_REGISTRY.doraemon.styles;
  return styles[style] ?? styles.multi_panel;
}
