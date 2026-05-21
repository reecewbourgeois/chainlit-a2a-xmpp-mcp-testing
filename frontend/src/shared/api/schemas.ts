import z from "zod";

export const SupportedInputSchema = z.object({
  audio_input: z.boolean(),
  vision_input: z.boolean(),
});
export type SupportedInput = z.infer<typeof SupportedInputSchema>;
