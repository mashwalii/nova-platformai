import type { Localized } from "./mockNews";
import chipsImage from "@/assets/nova-chips.jpg";
import modelImage from "@/assets/nova-open-model.jpg";
import roboticsImage from "@/assets/nova-robotics.jpg";
const l = (en: string, ar: string): Localized => ({ en, ar });
export type Course = { id: string; title: Localized; platform: string; category: Localized; level: Localized; duration: Localized; language: Localized; image: string; featured?: boolean; url: string };
export const courseCategories = [l("All", "الكل"), l("Programming", "البرمجة"), l("AI", "الذكاء الاصطناعي"), l("Machine Learning", "تعلم الآلة"), l("Data Science", "علم البيانات"), l("Computer Science", "علوم الحاسب"), l("Mathematics", "الرياضيات"), l("Web Development", "تطوير الويب"), l("Cybersecurity", "الأمن السيبراني")];
export const courses: Course[] = [
{id:"python-ai",title:l("Python for AI Builders","بايثون لبناة الذكاء الاصطناعي"),platform:"DeepLearning.AI",category:l("Programming","البرمجة"),level:l("Beginner","مبتدئ"),duration:l("6 weeks","6 أسابيع"),language:l("English","الإنجليزية"),image:modelImage,featured:true,url:"https://www.deeplearning.ai/"},
{id:"ml-foundations",title:l("Machine Learning Foundations","أساسيات تعلم الآلة"),platform:"Google",category:l("Machine Learning","تعلم الآلة"),level:l("Intermediate","متوسط"),duration:l("8 weeks","8 أسابيع"),language:l("English + Arabic captions","الإنجليزية مع ترجمة عربية"),image:chipsImage,featured:true,url:"https://developers.google.com/machine-learning"},
{id:"responsible-ai",title:l("Responsible AI in Practice","الذكاء الاصطناعي المسؤول عمليًا"),platform:"Microsoft Learn",category:l("AI","الذكاء الاصطناعي"),level:l("Intermediate","متوسط"),duration:l("4 weeks","4 أسابيع"),language:l("Arabic","العربية"),image:roboticsImage,url:"https://learn.microsoft.com/training/"},
{id:"data-analysis",title:l("Data Analysis with Python","تحليل البيانات باستخدام بايثون"),platform:"freeCodeCamp",category:l("Data Science","علم البيانات"),level:l("Beginner","مبتدئ"),duration:l("10 hours","10 ساعات"),language:l("English","الإنجليزية"),image:modelImage,url:"https://www.freecodecamp.org/"},
{id:"cyber-basics",title:l("Cybersecurity Fundamentals","أساسيات الأمن السيبراني"),platform:"Cisco Skills",category:l("Cybersecurity","الأمن السيبراني"),level:l("Beginner","مبتدئ"),duration:l("5 weeks","5 أسابيع"),language:l("Arabic","العربية"),image:chipsImage,url:"https://skillsforall.com/"},
{id:"web-systems",title:l("Modern Web Systems","أنظمة الويب الحديثة"),platform:"HarvardX",category:l("Web Development","تطوير الويب"),level:l("Advanced","متقدم"),duration:l("9 weeks","9 أسابيع"),language:l("English","الإنجليزية"),image:roboticsImage,url:"https://www.edx.org/"}
];
export const learningPaths = [
{title:l("AI Engineer","مهندس ذكاء اصطناعي"),steps:[l("Python","بايثون"),l("Data Science","علم البيانات"),l("Machine Learning","تعلم الآلة"),l("AI Systems","أنظمة الذكاء الاصطناعي")]},
{title:l("Security Analyst","محلل أمن سيبراني"),steps:[l("Networks","الشبكات"),l("Linux","لينكس"),l("Threats","التهديدات"),l("Defense","الدفاع")]}
];
