import re

with open('C:/Users/athir/Downloads/app/app/dashboard/integrations/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

modals_ui = '''
        <GmailSyncModal
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

# Find the insertion point before the final closing </div> or alongside GoogleDriveFolderModal
marker = '<GoogleDriveFolderModal'

if marker in content:
    content = content.replace(marker, modals_ui + '\n        ' + marker)
    with open('C:/Users/athir/Downloads/app/app/dashboard/integrations/page.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Modals inserted successfully!")
else:
    print("Marker not found. Could not insert modals.")
