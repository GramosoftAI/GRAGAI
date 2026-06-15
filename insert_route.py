with open('app/modules/agents/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

route_code = '''
@router.get(
    "/{agent_id}/integration/{integration_type}",
    response_model=dict,
    summary="Get Integration Status",
    description="Returns true if the agent is connected to the specified integration",
)
async def get_integration_status(
    request: Request,
    agent_id: str,
    integration_type: str,
) -> dict:
    """
    Check if a specific integration is active for this agent.
    """
    try:
        tenant_id, _ = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            service = AgentService(db, tenant_id)
            result = await service.get_agent(agent_id)
            
            if not result.get("success"):
                status_code = result.get("status_code", 404)
                error_msg = result.get("error", "Agent not found")
                raise HTTPException(status_code=status_code, detail=error_msg)
                
            agent_data = result["data"]["agent"]
            connected_integrations = agent_data.get("connected_integrations", [])
            
            is_connected = integration_type in connected_integrations
            
            from .utils import format_success
            return format_success({
                "integration_type": integration_type,
                "is_connected": is_connected
            }, meta={"message": "Status fetched successfully"})
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting integration status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
'''

idx = content.find('@router.patch(')

new_content = content[:idx] + route_code + '\n\n' + content[idx:]

with open('app/modules/agents/routes.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
