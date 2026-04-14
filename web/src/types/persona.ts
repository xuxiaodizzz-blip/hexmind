export interface Persona {
  id: string;
  name: string;
  role: string;
  domain: 'tech' | 'business' | 'medical' | 'creative' | 'custom';
  description: string;
  prompt: string;
  avatar: string;
  tags: string[];
  isPublic: boolean;
  isCustom: boolean;
  sprints?: number;
}
