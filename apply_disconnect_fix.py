import re

file_path = 'C:/Users/athir/Downloads/app/app/dashboard/integrations/page.tsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

google_disconnect_orig = """  const handleGoogleDisconnect = () => {
    disconnect({ path: `${agentkbres}` })
      .then((res: any) => {
        if (res.ok) {
          setGoogleStatus("Connect");
          checkConnection();
        }
      })
      .catch((err: any) => console.log(err));
  };"""

google_disconnect_new = """  const handleGoogleDisconnect = async () => {
    try {
      const token = getCookie("AUTH_TOKEN");
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/knowledge-bases/agent/${agent?.id}/integration/google_drive`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setGoogleStatus("Connect");
        checkConnection();
      }
    } catch (err) {
      console.error(err);
    }
  };"""

sharepoint_disconnect_orig = """  const handleSharePointDisconnect = () => {
    disconnect({ path: `${agentkbres}` })
      .then((res: any) => {
        if (res.ok) {
          setSharePointStatus("Connect");
          checkConnection();
        }
      })
      .catch((err: any) => console.log(err));
  };"""

sharepoint_disconnect_new = """  const handleSharePointDisconnect = async () => {
    try {
      const token = getCookie("AUTH_TOKEN");
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/knowledge-bases/agent/${agent?.id}/integration/sharepoint`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setSharePointStatus("Connect");
        checkConnection();
      }
    } catch (err) {
      console.error(err);
    }
  };"""

content = content.replace(google_disconnect_orig, google_disconnect_new)
content = content.replace(sharepoint_disconnect_orig, sharepoint_disconnect_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
