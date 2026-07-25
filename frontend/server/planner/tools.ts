import { tool } from 'ai';
import { z } from 'zod';
import type { Slide } from '@/features/projects/types';
import { DEFAULT_TEMPLATE_ID, getToolDescription, type TemplateId } from '@/shared/template-config';

export const SlideSchema = z.object({
  type: z
    .enum(['cover', 'introduction', 'content', 'summary', 'ending'])
    .describe('Type of the slide'),
  title: z.string().describe('Title of the slide'),
  description: z.string().describe('Brief description of what this slide is about'),
  content: z
    .string()
    .optional()
    .describe(
      'Detailed image generation prompt for the slide. Must follow the pattern: Subject + Action + Environment + Style/Color/Lighting. Text to be rendered should be in double quotes.'
    ),
});

export type SlideType = z.infer<typeof SlideSchema>['type'];

export function createPlannerTools(chatId: string, templateId: TemplateId = DEFAULT_TEMPLATE_ID) {
  const createPPTPlanTool = tool({
    description: getToolDescription(templateId),
    inputSchema: z.object({
      slides: z.array(SlideSchema).describe('Array of slides for the PPT plan'),
    }),
    async execute({ slides }) {
      if (!slides || slides.length === 0) {
        return {
          result: 'PPT Plan Cleared.',
          slides: [],
          projectId: chatId,
        };
      }

      const validatedSlides: Omit<Slide, 'id'>[] = slides.map(slide => ({
        type: slide.type,
        title: slide.title,
        description: slide.description,
        content: slide.content,
      }));

      return {
        result: 'PPT Plan Created Successfully!',
        slides: validatedSlides,
        projectId: chatId,
      };
    },
  });

  return {
    create_ppt_plan: createPPTPlanTool,
  };
}
