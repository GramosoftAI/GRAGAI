import React from "react";

export default function PrivacyPolicy() {
  return (
    <div 
      className="privacy-policy-container" 
      style={{ 
        background: "var(--bg, #ffffff)", 
        color: "var(--body, #414856)", 
        minHeight: "80vh",
        padding: "48px 20px 80px",
        fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif"
      }}
    >
      <div style={{ maxWidth: "920px", margin: "0 auto" }}>
        
        {/* Header Title & Date Badges */}
        <div 
          style={{ 
            background: "linear-gradient(135deg, rgba(15, 181, 161, 0.05) 0%, rgba(124, 108, 240, 0.05) 100%)",
            border: "1px solid var(--line, #e5e9ef)",
            borderRadius: "20px",
            padding: "40px 28px",
            textAlign: "center",
            marginBottom: "32px"
          }}
        >
          <div 
            style={{ 
              display: "inline-block", 
              padding: "4px 14px", 
              marginBottom: "16px", 
              borderRadius: "9999px", 
              fontWeight: 700, 
              textTransform: "uppercase", 
              background: "var(--teal-soft, #e3f7f3)", 
              color: "var(--teal-deep, #0a8576)", 
              fontSize: "12px", 
              letterSpacing: "0.05em" 
            }}
          >
            Legal &amp; Compliance
          </div>
          <h1 
            style={{ 
              color: "var(--ink, #14161f)", 
              fontSize: "clamp(28px, 4vw, 42px)", 
              fontWeight: 800, 
              letterSpacing: "-0.025em",
              marginBottom: "16px",
              lineHeight: 1.15
            }}
          >
            GSearchAI Privacy Policy
          </h1>
          <p 
            style={{ 
              maxWidth: "680px", 
              margin: "0 auto 24px", 
              fontSize: "16.5px", 
              color: "var(--muted, #6b7280)",
              lineHeight: 1.6
            }}
          >
            This Privacy Policy explains how GSearchAI collects, uses, processes, stores, and protects user and Google Drive data when using the GSearchAI platform and Google Drive connector.
          </p>
          
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "10px", fontSize: "13px" }}>
            <span 
              style={{ 
                background: "#ffffff", 
                color: "var(--ink, #14161f)", 
                border: "1px solid var(--line, #e5e9ef)", 
                padding: "6px 16px", 
                borderRadius: "9999px", 
                fontWeight: 600,
                boxShadow: "0 2px 4px rgba(0,0,0,0.02)"
              }}
            >
              <strong>Effective Date:</strong> September 4, 2026
            </span>
            <span 
              style={{ 
                background: "#ffffff", 
                color: "var(--ink, #14161f)", 
                border: "1px solid var(--line, #e5e9ef)", 
                padding: "6px 16px", 
                borderRadius: "9999px", 
                fontWeight: 600,
                boxShadow: "0 2px 4px rgba(0,0,0,0.02)"
              }}
            >
              <strong>Last Updated:</strong> September 4, 2026
            </span>
            <span 
              style={{ 
                background: "#ffffff", 
                color: "var(--ink, #14161f)", 
                border: "1px solid var(--line, #e5e9ef)", 
                padding: "6px 16px", 
                borderRadius: "9999px", 
                fontWeight: 600,
                boxShadow: "0 2px 4px rgba(0,0,0,0.02)"
              }}
            >
              <strong>Operated by:</strong> Gramosoft Private Limited
            </span>
          </div>
        </div>

        {/* Google API Services User Data Policy Banner */}
        <div 
          style={{ 
            background: "var(--teal-soft, #e3f7f3)", 
            border: "1.5px solid rgba(15, 181, 161, 0.3)", 
            borderRadius: "16px",
            padding: "24px 28px",
            marginBottom: "36px",
            boxShadow: "0 6px 20px -8px rgba(15, 181, 161, 0.2)"
          }}
        >
          <h3 
            style={{ 
              color: "var(--teal-deep, #0a8576)", 
              fontSize: "18px", 
              fontWeight: 700, 
              marginTop: 0,
              marginBottom: "12px" 
            }}
          >
            Google API Services User Data Policy
          </h3>
          <p style={{ fontSize: "15px", lineHeight: "1.6", color: "var(--ink, #14161f)", marginBottom: "12px" }}>
            GSearchAI&apos;s use and transfer to any other app of information received from Google APIs will adhere to the{" "}
            <a 
              href="https://developers.google.com/terms/api-services-user-data-policy" 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ color: "var(--teal-deep, #0a8576)", fontWeight: 700, textDecoration: "underline" }}
            >
              Google API Services User Data Policy
            </a>
            , including the Limited Use requirements.
          </p>
          <ul style={{ paddingLeft: "20px", margin: "0 0 16px", color: "var(--ink, #14161f)", fontSize: "14.5px" }}>
            <li style={{ marginBottom: "6px" }}><strong>GSearchAI does not sell Google user data.</strong></li>
            <li><strong>GSearchAI does not use Google user data to train, fine-tune, or develop generalized artificial intelligence or machine learning models.</strong></li>
          </ul>
          <div style={{ paddingTop: "12px", borderTop: "1px solid rgba(15, 181, 161, 0.2)" }}>
            <a 
              href="https://developers.google.com/terms/api-services-user-data-policy" 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ 
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "7px 16px",
                borderRadius: "9999px",
                border: "1.5px solid var(--teal, #0fb5a1)",
                color: "var(--teal-deep, #0a8576)",
                background: "#ffffff",
                fontWeight: 700,
                fontSize: "13.5px",
                textDecoration: "none"
              }}
            >
              Read Google API Services User Data Policy &rarr;
            </a>
          </div>
        </div>

        {/* Policy Content Sections */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px", fontSize: "15.5px", lineHeight: "1.7" }}>
          
          {/* Section 1 */}
          <section 
            id="section-1" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              1. Introduction
            </h2>
            <p style={{ marginTop: 0, marginBottom: "12px" }}>
              GSearchAI is an enterprise AI search and Retrieval-Augmented Generation (RAG) platform that helps users search, retrieve, and analyze documents across cloud applications and databases using natural language.
            </p>
            <p style={{ marginBottom: 0 }}>
              This Privacy Policy explains how GSearchAI collects, accesses, uses, processes, stores, and protects information when you use the GSearchAI website, platform, and third-party integrations, including the Google Drive connector.
            </p>
          </section>

          {/* Section 2 */}
          <section 
            id="section-2" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              2. Google Drive Data Access
            </h2>
            <p style={{ marginTop: 0, marginBottom: "14px" }}>
              When you connect Google Drive to GSearchAI, the application may access information necessary to provide the requested integration and search functionality.
            </p>
            <p style={{ fontWeight: 700, color: "var(--ink, #14161f)", marginBottom: "12px" }}>This may include:</p>
            
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px", marginBottom: "16px" }}>
              <div style={{ background: "var(--alt, #f5f7fa)", border: "1px solid var(--line, #e5e9ef)", borderRadius: "12px", padding: "18px" }}>
                <h3 style={{ color: "var(--teal-deep, #0a8576)", fontSize: "15px", fontWeight: 700, marginTop: 0, marginBottom: "10px" }}>
                  File Metadata
                </h3>
                <ul style={{ paddingLeft: "18px", margin: 0, fontSize: "14.5px", color: "var(--body, #414856)" }}>
                  <li>File names</li>
                  <li>File IDs</li>
                  <li>MIME types</li>
                  <li>Created and modified timestamps</li>
                  <li>Folder structures</li>
                </ul>
              </div>

              <div style={{ background: "var(--alt, #f5f7fa)", border: "1px solid var(--line, #e5e9ef)", borderRadius: "12px", padding: "18px" }}>
                <h3 style={{ color: "var(--teal-deep, #0a8576)", fontSize: "15px", fontWeight: 700, marginTop: 0, marginBottom: "10px" }}>
                  Document Content
                </h3>
                <p style={{ fontSize: "13.5px", color: "var(--muted, #6b7280)", marginTop: 0, marginBottom: "8px" }}>For files explicitly selected or made available for indexing:</p>
                <ul style={{ paddingLeft: "18px", margin: 0, fontSize: "14.5px", color: "var(--body, #414856)" }}>
                  <li>Google Docs</li>
                  <li>PDF files</li>
                  <li>Microsoft Word documents</li>
                  <li>Microsoft Excel files</li>
                  <li>CSV files</li>
                </ul>
              </div>
            </div>

            <div style={{ background: "var(--alt, #f5f7fa)", border: "1px solid var(--line, #e5e9ef)", borderRadius: "12px", padding: "18px", marginBottom: "16px" }}>
              <h3 style={{ color: "var(--teal-deep, #0a8576)", fontSize: "15px", fontWeight: 700, marginTop: 0, marginBottom: "8px" }}>
                User Account Information
              </h3>
              <p style={{ fontSize: "14.5px", color: "var(--body, #414856)", margin: 0 }}>
                GSearchAI may access your Google account email address to authenticate your connection and associate the integration with the appropriate GSearchAI workspace or tenant.
              </p>
            </div>

            <h3 style={{ color: "var(--ink, #14161f)", fontSize: "16px", fontWeight: 700, marginBottom: "8px" }}>Purpose of Access</h3>
            <p style={{ fontSize: "14.5px", color: "var(--muted, #6b7280)", marginTop: 0, marginBottom: "8px" }}>Google Drive data is accessed only to provide functionality such as:</p>
            <ul style={{ paddingLeft: "20px", margin: 0, fontSize: "14.5px" }}>
              <li>Searching documents</li>
              <li>Retrieving relevant information</li>
              <li>Processing documents</li>
              <li>Indexing content</li>
              <li>Generating answers to user queries</li>
              <li>Supporting knowledge-base functionality</li>
            </ul>
          </section>

          {/* Section 3 */}
          <section 
            id="section-3" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              3. How We Use Your Data
            </h2>
            <p style={{ marginTop: 0, marginBottom: "14px" }}>GSearchAI may process connected data for the following purposes:</p>

            <div style={{ marginBottom: "16px" }}>
              <h3 style={{ color: "var(--ink, #14161f)", fontSize: "16px", fontWeight: 700, marginTop: 0, marginBottom: "6px" }}>Document Processing</h3>
              <p style={{ fontSize: "14.5px", color: "var(--muted, #6b7280)", marginTop: 0, marginBottom: "10px" }}>Documents may be processed through:</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {["Document parsing", "Chunking", "Text extraction", "Vector embedding generation", "Metadata extraction"].map((item, idx) => (
                  <span 
                    key={idx} 
                    style={{ 
                      background: "var(--alt, #f5f7fa)", 
                      border: "1px solid var(--line, #e5e9ef)", 
                      padding: "4px 12px", 
                      borderRadius: "6px",
                      fontSize: "13.5px",
                      fontWeight: 600,
                      color: "var(--ink, #14161f)"
                    }}
                  >
                    &bull; {item}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <h3 style={{ color: "var(--ink, #14161f)", fontSize: "16px", fontWeight: 700, marginTop: 0, marginBottom: "6px" }}>Tabular Data Processing</h3>
              <p style={{ fontSize: "14.5px", color: "var(--body, #414856)", margin: 0 }}>
                Excel and CSV files may be converted into structured formats for analytics and querying.
              </p>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <h3 style={{ color: "var(--ink, #14161f)", fontSize: "16px", fontWeight: 700, marginTop: 0, marginBottom: "6px" }}>Retrieval-Augmented Generation</h3>
              <p style={{ fontSize: "14.5px", color: "var(--body, #414856)", margin: 0 }}>
                Relevant document snippets may be temporarily provided to configured AI/LLM services to construct responses to user queries.
              </p>
            </div>

            <div 
              style={{ 
                background: "#fffbe6", 
                border: "1px solid #ffe58f", 
                borderRadius: "10px", 
                padding: "16px" 
              }}
            >
              <h3 style={{ color: "#873800", fontSize: "15px", fontWeight: 700, marginTop: 0, marginBottom: "4px" }}>
                No AI Model Training
              </h3>
              <p style={{ fontSize: "14px", color: "#613400", margin: 0 }}>
                Google Drive files, document chunks, and search queries are not used by GSearchAI to train, fine-tune, or develop generalized public or foundation AI models.
              </p>
            </div>
          </section>

          {/* Section 4 */}
          <section 
            id="section-4" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              4. How We Store Your Data
            </h2>
            <p style={{ marginTop: 0, marginBottom: "12px" }}>
              Depending on the functionality being used, GSearchAI may store processed information in application infrastructure such as:
            </p>

            <ul style={{ paddingLeft: "20px", marginTop: 0, marginBottom: "16px" }}>
              <li style={{ marginBottom: "6px" }}><strong>PostgreSQL / pgvector</strong> for text, metadata, and vector embeddings</li>
              <li style={{ marginBottom: "6px" }}><strong>Neo4j</strong> for graph relationships and topology</li>
              <li style={{ marginBottom: "6px" }}><strong>Parquet datasets</strong> for tabular data processing</li>
              <li><strong>DuckDB</strong> for querying structured/tabular datasets</li>
            </ul>

            <p style={{ marginBottom: "8px" }}>Data is protected using appropriate technical and organizational security measures.</p>
            <p style={{ marginBottom: "8px" }}>Communication with GSearchAI services is protected using HTTPS/TLS.</p>
            <p style={{ marginBottom: 0 }}>OAuth credentials and tokens are protected using encryption and appropriate access controls.</p>
          </section>

          {/* Section 5 */}
          <section 
            id="section-5" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              5. Google Drive Permissions
            </h2>
            <p style={{ marginTop: 0, marginBottom: "12px" }}>GSearchAI may request Google permissions necessary to provide the Google Drive integration.</p>
            <p style={{ fontWeight: 700, color: "var(--ink, #14161f)", marginBottom: "10px" }}>Examples include:</p>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px" }}>
              <code style={{ background: "var(--alt, #f5f7fa)", border: "1px solid var(--line, #e5e9ef)", padding: "8px 14px", borderRadius: "6px", fontSize: "13.5px", color: "var(--ink, #14161f)", wordBreak: "break-all" }}>
                https://www.googleapis.com/auth/drive.readonly
              </code>
              <code style={{ background: "var(--alt, #f5f7fa)", border: "1px solid var(--line, #e5e9ef)", padding: "8px 14px", borderRadius: "6px", fontSize: "13.5px", color: "var(--ink, #14161f)", wordBreak: "break-all" }}>
                https://www.googleapis.com/auth/userinfo.email
              </code>
            </div>

            <p style={{ marginBottom: "8px" }}><strong>GSearchAI does not request or store your Google account password.</strong></p>
            <p style={{ margin: 0, color: "var(--muted, #6b7280)" }}>
              OAuth credentials are protected and used only to maintain the authorized connection between your Google account and GSearchAI.
            </p>
          </section>

          {/* Section 6 */}
          <section 
            id="section-6" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              6. Data Sharing
            </h2>
            <ul style={{ paddingLeft: "20px", marginTop: 0, marginBottom: "14px" }}>
              <li style={{ marginBottom: "6px" }}>GSearchAI does not sell, rent, or trade Google Drive data.</li>
              <li>Google Drive information is not shared with advertisers or data brokers.</li>
            </ul>
            <p style={{ margin: 0, color: "var(--muted, #6b7280)" }}>
              GSearchAI may use third-party infrastructure or AI/cloud service providers to provide application functionality. Such providers may process limited information as necessary to provide the requested service and are subject to applicable contractual and data-protection requirements.
            </p>
          </section>

          {/* Section 7 */}
          <section 
            id="section-7" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              7. Data Retention and Deletion
            </h2>
            <p style={{ marginTop: 0, marginBottom: "12px" }}>Data may be retained while the associated GSearchAI knowledge base or account remains active.</p>
            <p style={{ marginBottom: "12px" }}>
              When a user deletes applicable content, knowledge-base data, or an account, GSearchAI will process the deletion of associated application data according to its operational deletion procedures.
            </p>
            <p style={{ fontWeight: 700, color: "var(--ink, #14161f)", marginBottom: "8px" }}>This may include:</p>
            <ul style={{ paddingLeft: "20px", margin: 0 }}>
              <li>Document chunks</li>
              <li>Vector embeddings</li>
              <li>Graph data</li>
              <li>Structured datasets</li>
              <li>OAuth connection information</li>
            </ul>
          </section>

          {/* Section 8 */}
          <section 
            id="section-8" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              8. Your Rights
            </h2>
            <p style={{ marginTop: 0, marginBottom: "12px" }}>Depending on your location and applicable law, you may have rights including:</p>
            <ul style={{ paddingLeft: "20px", marginTop: 0, marginBottom: "14px" }}>
              <li>Access to your personal information</li>
              <li>Requesting deletion</li>
              <li>Requesting correction of inaccurate information</li>
              <li>Requesting restriction of processing</li>
              <li>Disconnecting third-party integrations</li>
            </ul>
            <p style={{ margin: 0, fontSize: "14px", color: "var(--muted, #6b7280)" }}>
              These rights may be subject to applicable legal requirements and exceptions.
            </p>
          </section>

          {/* Section 9 */}
          <section 
            id="section-9" 
            style={{ 
              background: "#ffffff", 
              border: "1px solid var(--line, #e5e9ef)", 
              borderRadius: "16px", 
              padding: "28px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.01)"
            }}
          >
            <h2 style={{ color: "var(--ink, #14161f)", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              9. Disconnecting Google Drive
            </h2>
            <p style={{ marginTop: 0, marginBottom: "10px" }}>You can disconnect Google Drive from GSearchAI through:</p>
            <div style={{ background: "var(--alt, #f5f7fa)", border: "1px solid var(--line, #e5e9ef)", padding: "12px 16px", borderRadius: "8px", marginBottom: "16px", fontWeight: 600, fontSize: "14px", color: "var(--ink, #14161f)" }}>
              GSearchAI Dashboard &rarr; Settings &rarr; Integrations &rarr; Google Drive &rarr; Disconnect Connection
            </div>
            
            <p style={{ marginBottom: "8px" }}>You can also manage third-party application permissions through your Google Account:</p>
            <p style={{ marginBottom: "10px" }}>
              <a 
                href="https://myaccount.google.com/permissions" 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ color: "var(--teal-deep, #0a8576)", fontWeight: 700, textDecoration: "underline" }}
              >
                https://myaccount.google.com/permissions &rarr;
              </a>
            </p>
            <p style={{ margin: 0, fontSize: "14px", color: "var(--muted, #6b7280)" }}>
              Find GSearchAI and remove its access if you no longer want the application to access your Google account.
            </p>
          </section>

          {/* Section 10 */}
          <section 
            id="section-10" 
            style={{ 
              background: "linear-gradient(135deg, #14161f 0%, #1e212f 100%)", 
              border: "1px solid var(--line-2, #d9dfe8)", 
              borderRadius: "16px", 
              padding: "32px",
              color: "#ffffff"
            }}
          >
            <h2 style={{ color: "#ffffff", fontSize: "20px", fontWeight: 700, marginTop: 0, marginBottom: "14px" }}>
              10. Contact Us
            </h2>
            <p style={{ fontWeight: 700, margin: "0 0 4px", fontSize: "16px" }}>Gramosoft Private Limited</p>
            <p style={{ margin: "0 0 20px", color: "rgba(255,255,255,0.8)" }}>GSearchAI</p>
            
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
              <div style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "10px", padding: "14px" }}>
                <span style={{ display: "block", textTransform: "uppercase", fontSize: "11px", fontWeight: 700, color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>Privacy</span>
                <a href="mailto:privacy@gsearchai.com" style={{ color: "#ffffff", fontWeight: 700, textDecoration: "none" }}>
                  privacy@gsearchai.com
                </a>
              </div>
              
              <div style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "10px", padding: "14px" }}>
                <span style={{ display: "block", textTransform: "uppercase", fontSize: "11px", fontWeight: 700, color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>Support</span>
                <a href="mailto:support@gsearchai.com" style={{ color: "#ffffff", fontWeight: 700, textDecoration: "none" }}>
                  support@gsearchai.com
                </a>
              </div>

              <div style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "10px", padding: "14px" }}>
                <span style={{ display: "block", textTransform: "uppercase", fontSize: "11px", fontWeight: 700, color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>Website</span>
                <a href="https://gsearchai.com" target="_blank" rel="noopener noreferrer" style={{ color: "#ffffff", fontWeight: 700, textDecoration: "none" }}>
                  https://gsearchai.com &rarr;
                </a>
              </div>
            </div>

            <p style={{ marginTop: "24px", marginBottom: 0, color: "rgba(255,255,255,0.7)", fontSize: "13.5px" }}>
              For privacy-related requests, contact us using the privacy email address above.
            </p>
          </section>

        </div>
      </div>
    </div>
  );
}
