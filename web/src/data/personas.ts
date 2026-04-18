import type { Persona } from '../types/persona';

/**
 * System personas — synced from backend YAML definitions.
 * These are read-only on the frontend; the backend resolves them by ID.
 *
 * Backend API constraints:
 *   persona_ids: 2–5 IDs from this list
 *   config.execution_token_cap: 5,000–500,000 (default 50,000)
 *   config.selected_model: backend-defined alias (default from /api/settings)
 *   config.discussion_locale: "zh" | "en"
 */
export const SYSTEM_PERSONAS: Persona[] = [
  // ── Tech ──────────────────────────────────────────
  {
    id: 'backend-engineer',
    name: '后端工程师',
    nameEn: 'Backend Engineer',
    role: 'Backend Engineer',
    domain: 'tech',
    description: '资深后端开发，精通分布式系统、API 设计、数据库优化和微服务架构。',
    descriptionEn: 'Senior backend developer skilled in distributed systems, API design, database optimization, and microservices architecture.',
    prompt: '你从服务端工程的视角分析问题，关注可靠性、可维护性和技术可行性。',
    avatar: '',
    tags: ['分布式系统', 'API 设计', '数据库'],
    tagsEn: ['Distributed Systems', 'API Design', 'Database'],
    isPublic: true,
    isCustom: false,
    sprints: 980,
  },
  {
    id: 'frontend-engineer',
    name: '前端工程师',
    nameEn: 'Frontend Engineer',
    role: 'Frontend Engineer',
    domain: 'tech',
    description: '资深前端开发，精通 React/Vue 生态、性能优化、可访问性和用户体验工程。',
    descriptionEn: 'Senior frontend developer skilled in React/Vue ecosystem, performance optimization, accessibility, and UX engineering.',
    prompt: '你从用户体验和前端工程的视角分析问题。',
    avatar: '',
    tags: ['React/Vue', '性能优化', 'UX'],
    tagsEn: ['React/Vue', 'Performance', 'UX'],
    isPublic: true,
    isCustom: false,
    sprints: 630,
  },
  {
    id: 'tech-lead',
    name: '技术负责人',
    nameEn: 'Tech Lead',
    role: 'Tech Lead',
    domain: 'tech',
    description: '技术团队负责人，擅长技术选型、架构决策、团队协作和技术债务管理。',
    descriptionEn: 'Tech team lead experienced in technology selection, architecture decisions, team coordination, and tech debt management.',
    prompt: '你从技术管理者的视角分析问题，平衡技术理想与交付现实。',
    avatar: '',
    tags: ['架构决策', '技术选型', '团队管理'],
    tagsEn: ['Architecture', 'Tech Selection', 'Team Management'],
    isPublic: true,
    isCustom: false,
    sprints: 540,
  },
  {
    id: 'devops-engineer',
    name: 'DevOps 工程师',
    nameEn: 'DevOps Engineer',
    role: 'DevOps Engineer',
    domain: 'tech',
    description: '资深 DevOps，精通 CI/CD、容器编排、云基础设施和可观测性体系。',
    descriptionEn: 'Senior DevOps engineer skilled in CI/CD, container orchestration, cloud infrastructure, and observability.',
    prompt: '你从运维和基础设施的视角分析问题，关注稳定性、自动化和成本效率。',
    avatar: '',
    tags: ['CI/CD', 'K8s', '云架构'],
    tagsEn: ['CI/CD', 'K8s', 'Cloud'],
    isPublic: true,
    isCustom: false,
    sprints: 412,
  },

  // ── Business ──────────────────────────────────────
  {
    id: 'product-manager',
    name: '产品经理',
    nameEn: 'Product Manager',
    role: 'Product Manager',
    domain: 'business',
    description: '资深产品经理，擅长需求分析、用户研究、路线图规划和跨团队协调。',
    descriptionEn: 'Senior product manager skilled in requirements analysis, user research, roadmap planning, and cross-team coordination.',
    prompt: '你从产品和用户需求的视角分析问题，关注 PMF 和用户价值。',
    avatar: '',
    tags: ['需求分析', 'PMF', '路线图'],
    tagsEn: ['Requirements', 'PMF', 'Roadmap'],
    isPublic: true,
    isCustom: false,
    sprints: 720,
  },
  {
    id: 'cfo',
    name: '首席财务官',
    nameEn: 'CFO',
    role: 'CFO',
    domain: 'business',
    description: '企业财务负责人，精通财务建模、成本控制、投资回报分析和风险量化。',
    descriptionEn: 'Chief Financial Officer skilled in financial modeling, cost control, ROI analysis, and risk quantification.',
    prompt: '你从财务和投资回报的视角分析问题，用数据说话，关注底线。',
    avatar: '',
    tags: ['财务建模', 'ROI', '风险量化'],
    tagsEn: ['Financial Modeling', 'ROI', 'Risk Quantification'],
    isPublic: true,
    isCustom: false,
    sprints: 540,
  },
  {
    id: 'growth-lead',
    name: '增长负责人',
    nameEn: 'Growth Lead',
    role: 'Growth Lead',
    domain: 'business',
    description: '增长团队负责人，精通用户增长、转化优化、数据驱动实验和渠道策略。',
    descriptionEn: 'Growth team lead skilled in user acquisition, conversion optimization, data-driven experiments, and channel strategy.',
    prompt: '你从增长和获客的视角分析问题，数据驱动，关注可规模化的增长杠杆。',
    avatar: '',
    tags: ['用户增长', '转化优化', '渠道策略'],
    tagsEn: ['User Growth', 'Conversion', 'Channel Strategy'],
    isPublic: true,
    isCustom: false,
    sprints: 856,
  },

  // ── Medical ───────────────────────────────────────
  {
    id: 'clinical-researcher',
    name: '临床研究员',
    nameEn: 'Clinical Researcher',
    role: 'Clinical Researcher',
    domain: 'medical',
    description: '资深临床研究人员，精通循证医学、临床试验设计、数据分析和文献评价。',
    descriptionEn: 'Senior clinical researcher skilled in evidence-based medicine, clinical trial design, data analysis, and literature review.',
    prompt: '你从循证医学的视角分析问题，要求证据等级明确，区分因果与相关。',
    avatar: '',
    tags: ['循证医学', '临床试验', '文献评价'],
    tagsEn: ['Evidence-Based', 'Clinical Trials', 'Literature Review'],
    isPublic: true,
    isCustom: false,
    sprints: 412,
  },
  {
    id: 'bioethicist',
    name: '生物伦理学家',
    nameEn: 'Bioethicist',
    role: 'Bioethicist',
    domain: 'medical',
    description: '生物伦理学专家，精通医学伦理审查、知情同意、公平性分析和政策影响评估。',
    descriptionEn: 'Bioethics expert skilled in medical ethics review, informed consent, fairness analysis, and policy impact assessment.',
    prompt: '你从伦理和社会影响的视角分析问题，确保决策在道德上站得住脚。',
    avatar: '',
    tags: ['伦理审查', '知情同意', '政策影响'],
    tagsEn: ['Ethics Review', 'Informed Consent', 'Policy Impact'],
    isPublic: true,
    isCustom: false,
    sprints: 280,
  },
  {
    id: 'hospital-admin',
    name: '医院管理者',
    nameEn: 'Hospital Admin',
    role: 'Hospital Admin',
    domain: 'medical',
    description: '医院运营管理者，精通医疗资源配置、合规管理、成本控制和患者体验优化。',
    descriptionEn: 'Hospital operations manager skilled in healthcare resource allocation, compliance, cost control, and patient experience optimization.',
    prompt: '你从医院运营管理的视角分析问题，平衡医疗质量与运营效率。',
    avatar: '',
    tags: ['医疗资源', '合规管理', '运营效率'],
    tagsEn: ['Healthcare Resources', 'Compliance', 'Operations'],
    isPublic: true,
    isCustom: false,
    sprints: 320,
  },
];

export const LLM_MODELS = [
  { label: 'GPT-4o', value: 'gpt-4o', description: 'OpenAI · 综合能力最强', descriptionEn: 'OpenAI · Best overall' },
  { label: 'GPT-4o-mini', value: 'gpt-4o-mini', description: 'OpenAI · 快速低成本', descriptionEn: 'OpenAI · Fast & affordable' },
  { label: 'Claude 3.5 Sonnet', value: 'claude-3.5-sonnet', description: 'Anthropic · 分析推理', descriptionEn: 'Anthropic · Analytical reasoning' },
  { label: 'Llama 3 70B', value: 'llama-3-70b', description: 'Ollama Local · 本地隐私', descriptionEn: 'Ollama Local · Privacy-first' },
];

export const DOMAIN_TABS = [
  // NOTE: 'all' tab removed in favor of user-curated 'favorites'.
  // Favorites are stored client-side in localStorage (see Personas.tsx).
  { label: 'Favorites', value: 'favorites' },
  { label: 'Tech', value: 'tech' },
  { label: 'Business', value: 'business' },
  { label: 'Medical', value: 'medical' },
  { label: 'Custom', value: 'custom' },
];

/** Backend-enforced limits */
export const LIMITS = {
  TOKEN_BUDGET_MIN: 5_000,
  TOKEN_BUDGET_MAX: 500_000,
  TOKEN_BUDGET_DEFAULT: 50_000,
  TOKEN_BUDGET_STEP: 5_000,
  PERSONA_MIN: 2,
  PERSONA_MAX: 5,
  QUESTION_MIN: 5,
  QUESTION_MAX: 500,
};

/** Accepted file types for Assets page (AI-readable only) */
export const ACCEPTED_EXTENSIONS = [
  '.pdf', '.txt', '.md', '.csv', '.json',
  '.png', '.jpg', '.jpeg', '.webp', '.docx',
];

export const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'text/plain',
  'text/markdown',
  'text/csv',
  'application/json',
  'image/png',
  'image/jpeg',
  'image/webp',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
].join(',');

export const MAX_FILE_SIZE_MB = 20;
