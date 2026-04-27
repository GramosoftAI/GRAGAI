import { AgentItem } from "../components/ui/type";
import { create } from "zustand";

type StoreType = {
    userId:string;
    setUserId:(id:string)=>void;
    agentList:AgentItem[];
    setAgentList:(list:AgentItem[])=>void;
    
    // setUserId:(id:string)=>void;
}

export const useStore =create<StoreType>((set,get)=>({
    userId:"",
    setUserId(id) {
       set({ userId: id });
    //    return id;
    console.log(get().userId);
    },
    agentList:[],
    setAgentList(list){
        set({agentList:list})
    }
}))