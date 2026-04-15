import { useStore } from "../hooks/useStore";


const  userId  = useStore.getState().userId;
console.log(userId, "this for the api call to get the data for uder ");
export enum methods {
  get = "get",
  post = "post",
  put = "put",
  delete = "delete",
  patch = "patch",
}

export type endpointType = {
  url: string;
  method: methods;
  baseURL?: string;
  withCredentials?: boolean;
};

export const endpoints = {
  LOGIN: {
    url: "/auth/login",
    method: methods.post,
  },
  REGISTER: {
    url: "/auth/register",
    method: methods.post,
  },
  GETAGENTLIST:{
    url:`/agents`,
    method:methods.get,
    parameters:{userId}
  },
  CREATEAGENT:{
    url:"/agents",
    method:methods.post
  },
  DELETEAGENT:{
    url:"/agents",
    method:methods.delete
  },
  KNOWLEDGEBASE:{
    url:"/agents",
    method:methods.post
  }

} as const;

export type endpointsType = keyof typeof endpoints;