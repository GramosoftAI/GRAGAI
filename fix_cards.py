import re

with open('C:/Users/athir/Downloads/app/app/dashboard/integrations/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

cards_ui = '''
        <Card
          hoverable
          className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/5 hover:-translate-y-1"
          styles={{ body: { padding: '24px sm:32px' } }}
        >
          <div className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Image
                src="https://upload.wikimedia.org/wikipedia/commons/7/7e/Gmail_icon_%282020%29.svg"
                alt="Gmail"
                width={40}
                height={40}
              />
              <div className="ml-4">
                <div className="font-semibold text-lg text-[var(--app-text)]">Gmail</div>
                <div className="text-sm text-[var(--app-text-secondary)] mt-1">
                  Emails, threads, and attachments
                </div>
              </div>
            </div>

            <Tooltip title={!agent?.id ? "Please select an agent first" : ""}>
              {gmailStatus === "Connected" ? (
                <Flex>
                  <button
                    onClick={showGmailDisconnectConfirm}
                    style={{ cursor: "pointer" }}
                    className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                  >
                    Connected
                  </button>
                  <button
                    onClick={() => {}}
                    style={{ cursor: "pointer" }}
                    className="bg-purple-500 text-white px-4 py-2 rounded-lg ml-2"
                  >
                    +
                  </button>
                </Flex>
              ) : (
                <button
                  onClick={handleGmailConnect}
                  disabled={!agent?.id || gmailStatus === "Connecting"}
                  style={{ cursor: "pointer" }}
                  className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                >
                  {gmailStatus}
                </button>
              )}
            </Tooltip>
          </div>
        </Card>

        <Card
          hoverable
          className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/5 hover:-translate-y-1"
          styles={{ body: { padding: '24px sm:32px' } }}
        >
          <div className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Image
                src="https://upload.wikimedia.org/wikipedia/commons/d/df/Microsoft_Office_Outlook_%282018%E2%80%93present%29.svg"
                alt="Outlook"
                width={40}
                height={40}
              />
              <div className="ml-4">
                <div className="font-semibold text-lg text-[var(--app-text)]">Outlook</div>
                <div className="text-sm text-[var(--app-text-secondary)] mt-1">
                  Emails, folders, and attachments
                </div>
              </div>
            </div>

            <Tooltip title={!agent?.id ? "Please select an agent first" : ""}>
              {outlookStatus === "Connected" ? (
                <Flex>
                  <button
                    onClick={showOutlookDisconnectConfirm}
                    style={{ cursor: "pointer" }}
                    className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                  >
                    Connected
                  </button>
                  <button
                    onClick={() => {}}
                    style={{ cursor: "pointer" }}
                    className="bg-purple-500 text-white px-4 py-2 rounded-lg ml-2"
                  >
                    +
                  </button>
                </Flex>
              ) : (
                <button
                  onClick={handleOutlookConnect}
                  disabled={!agent?.id || outlookStatus === "Connecting"}
                  style={{ cursor: "pointer" }}
                  className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                >
                  {outlookStatus}
                </button>
              )}
            </Tooltip>
          </div>
        </Card>
'''

# Find the exact insertion point
match = re.search(r'(</Card>\s*</div>\s*</Flex>\s*\{\/\* Ecosystem Banner \*\/})', content)
if match:
    # Insert cards right after </Card> but before </div> (so it stays in the grid)
    # The structure is: 
    #   <div className="grid...">
    #     <Card>...</Card>
    #     <Card>...</Card>
    #   </div>
    # So we replace `</Card>\s*</div>\s*</Flex>`
    
    # Actually wait! In the current file:
    # 684:          </Card>
    # 685:         </div>
    # 686:         </Flex>
    
    new_content = re.sub(r'(</Card>\s*</div>\s*</Flex>\s*\{\/\* Ecosystem Banner \*\/})', r'</Card>\n' + cards_ui + r'\n        </div>\n        </Flex>\n\n        {/* Ecosystem Banner */}', content)
    
    with open('C:/Users/athir/Downloads/app/app/dashboard/integrations/page.tsx', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("UI Cards inserted successfully!")
else:
    print("Insertion point not found.")
