import './globals.css';

export const metadata = {
  title: 'BananaLecture Frontend',
  description: 'BananaLecture 的前端工作台，用于规划、编辑与预览 AI 讲解视频项目。',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
