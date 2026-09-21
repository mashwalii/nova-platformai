import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";
import type { Language } from "@/data/mockNews";

type AppContextValue = { language:Language; setLanguage:(value:Language)=>void; dark:boolean; toggleTheme:()=>void; saved:Set<string>; toggleSaved:(id:string)=>void; isSaved:(id:string)=>boolean; share:(id:string)=>void };
const AppContext=createContext<AppContextValue | undefined>(undefined);
export function AppProvider({children}:{children:ReactNode}){
 const [language,setLanguage]=useState<Language>("en"); const [dark,setDark]=useState(false); const [saved,setSaved]=useState<Set<string>>(new Set());
 useEffect(()=>{ const lang=localStorage.getItem("nova-language"); if(lang==="ar"||lang==="en") setLanguage(lang); setDark(localStorage.getItem("nova-theme")==="dark"); const stored=localStorage.getItem("nova-saved"); if(stored){try{setSaved(new Set(JSON.parse(stored) as string[]));}catch{setSaved(new Set());}} },[]);
 useEffect(()=>{ document.documentElement.lang=language; document.documentElement.dir=language==="ar"?"rtl":"ltr"; document.documentElement.classList.toggle("dark",dark); localStorage.setItem("nova-language",language); localStorage.setItem("nova-theme",dark?"dark":"light"); },[language,dark]);
 const toggleSaved=(id:string)=>setSaved(current=>{const next=new Set(current); const removing=next.has(id); removing?next.delete(id):next.add(id); localStorage.setItem("nova-saved",JSON.stringify([...next])); toast.success(language==="ar"?(removing?"تمت إزالة المقال من المحفوظات":"تم حفظ المقال"):(removing?"Article removed from saved":"Article saved")); return next;});
 const share=async(id:string)=>{const url=`${window.location.origin}/article/${id}`; try{await navigator.clipboard.writeText(url);toast.success(language==="ar"?"تم نسخ الرابط":"Link copied");}catch{toast.success(language==="ar"?"الرابط جاهز للمشاركة":"Share link ready");}};
 const value=useMemo(()=>({language,setLanguage,dark,toggleTheme:()=>setDark(v=>!v),saved,toggleSaved,isSaved:(id:string)=>saved.has(id),share}),[language,dark,saved]);
 return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
export function useApp(){const value=useContext(AppContext); if(!value) throw new Error("useApp must be used inside AppProvider"); return value;}
