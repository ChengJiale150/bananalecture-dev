export const STYLE_CONFIG: Record<
  string,
  {
    name: string;
    role: string;
    description: string;
    visualPrompt: string;
  }
> = {
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
};
