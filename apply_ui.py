import re

with open('C:/Users/athir/Downloads/app/app/dashboard/integrations/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
import_code = '''import GmailSyncModal from "./GmailSyncModal";
import OutlookSyncModal from "./OutlookSyncModal";
'''
content = content.replace('import SharePointFolderModal from "./SharePointFolderModal";', 'import SharePointFolderModal from "./SharePointFolderModal";\n' + import_code)

# Add state variables
state_code = '''  const [gmailStatus, setGmailStatus] = useState<"Connect" | "Connecting" | "Connected">("Connect");
  const [outlookStatus, setOutlookStatus] = useState<"Connect" | "Connecting" | "Connected">("Connect");
  const [gmailModal, setGmailModal] = useState(false);
  const [outlookModal, setOutlookModal] = useState(false);
'''
content = content.replace('const [sharePointModal, setSharePointModal] = useState(false);', 'const [sharePointModal, setSharePointModal] = useState(false);\n' + state_code)

# Add to checkConnection
check_code = '''        if (connectedIntegrations.includes("gmail")) {
          setGmailStatus("Connected");
        } else {
          setGmailStatus("Connect");
        }
        if (connectedIntegrations.includes("outlook")) {
          setOutlookStatus("Connected");
        } else {
          setOutlookStatus("Connect");
        }
'''
content = content.replace('setSharePointStatus("Connect");\n        }', 'setSharePointStatus("Connect");\n        }\n' + check_code)

# Add Connect Handlers
connect_handlers = '''  const handleGmailConnect = async () => {
    setGmailStatus("Connecting");
    try {
      const token = getCookie("AUTH_TOKEN");
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/knowledge-bases/${agentkbres}/gmail/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          credentials: {
            type: "service_account",
            client_email: process.env.NEXT_PUBLIC_GMAIL_CLIENT_EMAIL,
            private_key: process.env.NEXT_PUBLIC_GMAIL_PRIVATE_KEY,
          }
        }),
      });

      if (response.ok) {
        setGmailModal(true);
      } else {
        setGmailStatus("Connect");
        notification.error({ message: "Failed to register Gmail credentials" });
      }
    } catch (err) {
      console.error(err);
      setGmailStatus("Connect");
      notification.error({ message: "Error connecting to Gmail" });
    }
  };

  const handleOutlookConnect = async () => {
    setOutlookStatus("Connecting");
    try {
      const token = getCookie("AUTH_TOKEN");
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/knowledge-bases/${agentkbres}/outlook/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          credentials: {
            client_id: process.env.NEXT_PUBLIC_MS_CLIENT_ID || "",
            client_secret: process.env.NEXT_PUBLIC_MS_CLIENT_SECRET || "",
            tenant_id: process.env.NEXT_PUBLIC_MS_TENANT_ID || "common",
          }
        }),
      });

      if (response.ok) {
        setOutlookModal(true);
      } else {
        setOutlookStatus("Connect");
        notification.error({ message: "Failed to register Outlook credentials" });
      }
    } catch (err) {
      console.error(err);
      setOutlookStatus("Connect");
      notification.error({ message: "Error connecting to Outlook" });
    }
  };
'''
content = content.replace('const handleGoogleDisconnect = async () => {', connect_handlers + '\n  const handleGoogleDisconnect = async () => {')

# Add Disconnect Handlers
disconnect_handlers = '''  const handleGmailDisconnect = async () => {
    try {
      const token = getCookie("AUTH_TOKEN");
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/agents/${agent?.id}/integration/gmail`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setGmailStatus("Connect");
        checkConnection();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleOutlookDisconnect = async () => {
    try {
      const token = getCookie("AUTH_TOKEN");
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/agents/${agent?.id}/integration/outlook`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setOutlookStatus("Connect");
        checkConnection();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const showGmailDisconnectConfirm = () => {
    Modal.confirm({
      title: 'Disconnect Gmail?',
      content: 'Are you sure you want to disconnect your Gmail integration? This will remove synced emails.',
      okText: 'Disconnect',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk() { handleGmailDisconnect(); }
    });
  };

  const showOutlookDisconnectConfirm = () => {
    Modal.confirm({
      title: 'Disconnect Outlook?',
      content: 'Are you sure you want to disconnect your Outlook integration? This will remove synced emails.',
      okText: 'Disconnect',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk() { handleOutlookDisconnect(); }
    });
  };
'''
content = content.replace('const showGoogleDisconnectConfirm = () => {', disconnect_handlers + '\n  const showGoogleDisconnectConfirm = () => {')

# Add UI Cards
cards_ui = '''          {/* Gmail Card */}
          <div className="bg-[#14161C] border border-[#2A2E39] rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center p-2">
                <img
                  src="https://upload.wikimedia.org/wikipedia/commons/7/7e/Gmail_icon_%282020%29.svg"
                  alt="Gmail"
                  className="w-8 h-8"
                />
              </div>
              <div>
                <h3 className="text-white font-medium text-base mb-1">Gmail</h3>
                <p className="text-[#8B93A4] text-sm">Emails, threads, and attachments</p>
              </div>
            </div>
            {gmailStatus === "Connected" ? (
              <Button
                onClick={showGmailDisconnectConfirm}
                className="bg-[#8B5CF6] hover:bg-[#7C3AED] border-none text-white h-[42px] px-6 rounded-lg font-medium flex items-center gap-2"
              >
                Connected
                <span className="w-6 h-6 bg-white/20 rounded-md flex items-center justify-center ml-2">
                  +
                </span>
              </Button>
            ) : (
              <Button
                onClick={handleGmailConnect}
                loading={gmailStatus === "Connecting"}
                className="bg-transparent border border-[#2A2E39] text-white hover:text-white hover:border-[#8B5CF6] h-[42px] px-6 rounded-lg font-medium flex items-center gap-2"
              >
                {gmailStatus}
                <span className="w-6 h-6 bg-[#2A2E39] rounded-md flex items-center justify-center ml-2">
                  +
                </span>
              </Button>
            )}
          </div>

          {/* Outlook Card */}
          <div className="bg-[#14161C] border border-[#2A2E39] rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center p-2">
                <img
                  src="https://upload.wikimedia.org/wikipedia/commons/d/df/Microsoft_Office_Outlook_%282018%E2%80%93present%29.svg"
                  alt="Outlook"
                  className="w-8 h-8"
                />
              </div>
              <div>
                <h3 className="text-white font-medium text-base mb-1">Outlook</h3>
                <p className="text-[#8B93A4] text-sm">Emails, folders, and attachments</p>
              </div>
            </div>
            {outlookStatus === "Connected" ? (
              <Button
                onClick={showOutlookDisconnectConfirm}
                className="bg-[#8B5CF6] hover:bg-[#7C3AED] border-none text-white h-[42px] px-6 rounded-lg font-medium flex items-center gap-2"
              >
                Connected
                <span className="w-6 h-6 bg-white/20 rounded-md flex items-center justify-center ml-2">
                  +
                </span>
              </Button>
            ) : (
              <Button
                onClick={handleOutlookConnect}
                loading={outlookStatus === "Connecting"}
                className="bg-transparent border border-[#2A2E39] text-white hover:text-white hover:border-[#8B5CF6] h-[42px] px-6 rounded-lg font-medium flex items-center gap-2"
              >
                {outlookStatus}
                <span className="w-6 h-6 bg-[#2A2E39] rounded-md flex items-center justify-center ml-2">
                  +
                </span>
              </Button>
            )}
          </div>
'''
content = content.replace('</div>\n\n        {/* Modals */}', cards_ui + '\n        </div>\n\n        {/* Modals */}')

# Add Modal rendering
modals_ui = '''        <GmailSyncModal
          open={gmailModal}
          kbId={agentkbres}
          onClose={() => setGmailModal(false)}
          onSuccess={() => {
            setGmailModal(false);
            setGmailStatus("Connected");
            checkConnection();
          }}
        />

        <OutlookSyncModal
          open={outlookModal}
          kbId={agentkbres}
          onClose={() => setOutlookModal(false)}
          onSuccess={() => {
            setOutlookModal(false);
            setOutlookStatus("Connected");
            checkConnection();
          }}
        />
'''
content = content.replace('{/* Modals */}', '{/* Modals */}\n' + modals_ui)

with open('C:/Users/athir/Downloads/app/app/dashboard/integrations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
