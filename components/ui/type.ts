export type RegisterPayload = {
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  tenant_name: string;
};

// type.ts

export type Agent = {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  tenant_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
};

export type AgentListResponse = {
  success: boolean;
  data: {
    agents: Agent[];
    count: number;
    total: number;
  };
  error: null | string;
};

export type AgentItem = {
  id: string;
  name: string;
  status: string;
};

// const [getCreatedAgentList, res] = useAxios<AgentListResponse>({ endpoint: "GETAGENTLIST" });