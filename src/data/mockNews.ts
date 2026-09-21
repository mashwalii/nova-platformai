import heroImage from "@/assets/nova-reasoning-lab.jpg";
import openModelImage from "@/assets/nova-open-model.jpg";
import roboticsImage from "@/assets/nova-robotics.jpg";
import chipsImage from "@/assets/nova-chips.jpg";

export type NewsItem = {
  id: string;
  title: string;
  summary: string;
  category: string;
  source: string;
  time: string;
  readTime: string;
  image?: string;
  imageWidth?: number;
  imageHeight?: number;
  views?: string;
  comments?: string;
  featured?: boolean;
};

export const categories = [
  "All News", "Breaking News", "AI Research", "Generative AI", "AI Models",
  "AI Agents", "Robotics", "Computer Vision", "Open Source", "AI Companies",
  "AI Startups", "AI Tools", "AI Safety", "AI Policy", "AI Funding",
];

export const featuredStory: NewsItem = {
  id: "multimodal-reasoning",
  title: "A new multimodal system learns to reason across sight, sound and language",
  summary: "Researchers report a step-change in how foundation models connect visual evidence, spoken context and structured logic—without sacrificing response speed.",
  category: "AI Research",
  source: "NOVA Intelligence",
  time: "28 min ago",
  readTime: "6 min read",
  image: heroImage,
  imageWidth: 1600,
  imageHeight: 1000,
  views: "12.8K",
  comments: "184",
  featured: true,
};

export const briefs: NewsItem[] = [
  {
    id: "compute-fund",
    title: "VectorGrid closes $480M fund for frontier compute infrastructure",
    summary: "The new vehicle will back energy-efficient data centers and custom inference hardware.",
    category: "AI Funding", source: "Financial Ledger", time: "42 min ago", readTime: "3 min read",
  },
  {
    id: "benchmark",
    title: "Benchmark exposes hidden gaps in long-horizon agent planning",
    summary: "A 1,200-task evaluation finds even leading agents struggle to recover from early mistakes.",
    category: "AI Agents", source: "Arxiv Daily", time: "1 hr ago", readTime: "5 min read",
  },
  {
    id: "policy",
    title: "Global safety framework moves from principles to audits",
    summary: "The voluntary standard introduces shared reporting thresholds for frontier labs.",
    category: "AI Policy", source: "Policy Wire", time: "2 hrs ago", readTime: "4 min read",
  },
];

export const spotlight: NewsItem[] = [
  {
    id: "open-weights", title: "Open-weight model rivals proprietary systems on reasoning", summary: "A compact architecture is changing the economics of advanced model deployment.",
    category: "Open Source", source: "Model Review", time: "3 hrs ago", readTime: "7 min read", image: openModelImage, imageWidth: 1200, imageHeight: 800, views: "8.4K", comments: "96",
  },
  {
    id: "robot-learning", title: "Robots learn delicate assembly from a single demonstration", summary: "A new training method transfers dexterity across unfamiliar tools and environments.",
    category: "Robotics", source: "Robotics Lab", time: "4 hrs ago", readTime: "5 min read", image: roboticsImage, imageWidth: 1200, imageHeight: 800, views: "6.2K", comments: "71",
  },
  {
    id: "inference-chip", title: "The inference chip race enters its efficiency era", summary: "New silicon designs target lower energy use without compromising token throughput.",
    category: "AI Companies", source: "Circuit", time: "5 hrs ago", readTime: "8 min read", image: chipsImage, imageWidth: 1200, imageHeight: 800, views: "10.1K", comments: "128",
  },
];

export const allNews = [featuredStory, ...briefs, ...spotlight];