export interface Persona {
  id: string;
  name: string;
  nameEn?: string;
  role: string;
  domain: 'tech' | 'business' | 'medical' | 'creative' | 'custom';
  description: string;
  descriptionEn?: string;
  prompt: string;
  avatar: string;
  tags: string[];
  tagsEn?: string[];
  isPublic: boolean;
  isCustom: boolean;
  sprints?: number;
}
