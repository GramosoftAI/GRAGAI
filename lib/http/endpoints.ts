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
  GETAGENT:{
    url:"",
    method:methods.get
  },
  CREATEAGENT:{
    url:"/agents",
    method:methods.post
  },
  DELETEAGENT:{
    url:"",
    method:methods.delete
  }

} as const;

export type endpointsType = keyof typeof endpoints;