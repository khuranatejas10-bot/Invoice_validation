"use client";

import { useState, useRef } from "react";
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  Settings2, 
  AlertCircle,
  XCircle,
  ArrowLeft,
  Search,
  ChevronDown,
  ChevronRight,
  Shield,
  DollarSign,
  FileCheck,
  Link2,
  Network,
  Upload
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ValidationRule {
  rule: string;
  group: string;
  priority: number;
  status: string;
  message: string;
  evidence?: {
    page?: number;
    bbox?: number[];
    field?: string;
    value?: string;
    document_type?: string;
  } | null;
}

interface UploadedDocument {
  filename: string;
  classification: string;
  imageUrl?: string;
}

const MANDATORY_CATEGORIES = [
  "Invoice",
  "Purchase Order",
  "Bill of Quantity",
  "Delivery Challan",
  "DC Summary",
  "Work Completion",
  "Approval Email"
];


const GROUP_CONFIG: Record<string, { icon: typeof FileCheck; color: string; bgColor: string; borderColor: string }> = {
  "AI Agents & Classification": { icon: Network, color: "text-fuchsia-400", bgColor: "bg-fuchsia-500/10", borderColor: "border-fuchsia-500/20" },
  "Document & Quality Engines": { icon: FileCheck, color: "text-violet-400", bgColor: "bg-violet-500/10", borderColor: "border-violet-500/20" },
  "Data Matching & Reference Engines": { icon: Link2, color: "text-cyan-400", bgColor: "bg-cyan-500/10", borderColor: "border-cyan-500/20" },
  "Financial & Amount Engines": { icon: DollarSign, color: "text-amber-400", bgColor: "bg-amber-500/10", borderColor: "border-amber-500/20" },
  "Compliance, Rules & Governance": { icon: Shield, color: "text-emerald-400", bgColor: "bg-emerald-500/10", borderColor: "border-emerald-500/20" },
};

export default function UploadPortal() {
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  
  // Dashboard State
  const [isUploading, setIsUploading] = useState(false);
  const [isDashboardView, setIsDashboardView] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  
  const [missingDocs, setMissingDocs] = useState<string[]>([]);
  const [validationResults, setValidationResults] = useState<ValidationRule[]>([]);
  const [overallStatus, setOverallStatus] = useState("PENDING");
  const [documentImages, setDocumentImages] = useState<Record<string, string[]>>({});
  const [documentTexts, setDocumentTexts] = useState<Record<string, string>>({});
  const [classifiedDocs, setClassifiedDocs] = useState<UploadedDocument[]>([]);
  const [caseSubcategory, setCaseSubcategory] = useState("");
  
  // Accordion State
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(Object.keys(GROUP_CONFIG)));
  
  // Evidence Viewer
  const [activeEvidence, setActiveEvidence] = useState<{
    imageUrl?: string;
    rawText?: string;
    bbox: number[];
    field: string;
    value: string;
  } | null>(null);

  const handleFilesAdded = (newFiles: File[]) => {
    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const toggleGroup = (group: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setIsUploading(true);
    setUploadProgress("Uploading documents...");
    
    const extractedData: Record<string, any> = {};
    const uploadedTypes: string[] = [];
    const images: Record<string, string[]> = {};
    const texts: Record<string, string> = {};
    const docs: UploadedDocument[] = [];
    
    const projectId = Math.floor(Math.random() * 10000);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append("project_id", projectId.toString());
      formData.append("file", file);
      
      try {
        setUploadProgress(`Processing file ${i + 1} of ${files.length}...`);
        const res = await fetch(`${API_URL}/processing/upload_and_classify`, {
          method: "POST",
          body: formData,
        });
        const data = await res.json();
        
        docs.push({
          filename: file.name,
          classification: data.classification,
          imageUrl: data.image_url ? `${API_URL}${data.image_url}` : undefined
        });
        
        extractedData[data.classification] = data.extracted_fields;
        uploadedTypes.push(data.classification);
        texts[data.classification] = data.raw_text || "";
        
        if (data.image_urls && data.image_urls.length > 0) {
          images[data.classification] = data.image_urls.map((url: string) => `${API_URL}${url}`);
        } else if (data.image_url) {
          images[data.classification] = [`${API_URL}${data.image_url}`];
        }
      } catch (err) {
        console.error("Upload failed for", file.name, err);
      }
    }
    setDocumentImages(images);
    setDocumentTexts(texts);
    setClassifiedDocs(docs);

    // 2. Completeness Check
    setUploadProgress("Checking Completeness...");
    try {
      const compRes = await fetch(`${API_URL}/validation/completeness`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uploaded_doc_types: uploadedTypes })
      });
      const compData = await compRes.json();
      setMissingDocs(compData.missing || []);
    } catch (err) {
      console.error(err);
    }

    // 3. Rules Engine
    setUploadProgress("Running Unified Rules Engine...");
    try {
      const ruleRes = await fetch(`${API_URL}/processing/run_rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, extracted_data: extractedData })
      });
      const ruleData = await ruleRes.json();
      setValidationResults(ruleData.rule_results || []);
      setOverallStatus(ruleData.overall_status || "FAIL");
      setCaseSubcategory(ruleData.subcategory || "");
    } catch (err) {
      console.error(err);
    }

    setIsUploading(false);
    setIsDashboardView(true);
    setExpandedGroups(new Set(Object.keys(GROUP_CONFIG)));
  };

  const calculateRiskScore = () => {
    const totalChecks = validationResults.length + missingDocs.length;
    if (totalChecks === 0) return 0;
    
    const fails = validationResults.filter(r => r.status === "FAIL").length + missingDocs.length;
    return Math.max(0, Math.round(100 - ((fails / totalChecks) * 100)));
  };

  const groupedResults = validationResults.reduce<Record<string, ValidationRule[]>>((acc, rule) => {
    const group = rule.group || "Other";
    if (!acc[group]) acc[group] = [];
    acc[group].push(rule);
    return acc;
  }, {});

  const escapeRegExp = (str: string) => {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  const renderHighlightedText = (text: string, highlight: string) => {
    if (!highlight || !text) return text;
    const parts = text.split(new RegExp(`(${escapeRegExp(highlight)})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === highlight.toLowerCase() ? (
        <mark key={i} className="bg-yellow-500/30 text-yellow-200 px-1 py-0.5 rounded border border-yellow-500/50 font-bold animate-pulse">
          {part}
        </mark>
      ) : part
    );
  };

  const handleRuleClick = (rule: ValidationRule) => {
    console.log("Rule Clicked:", rule);
    console.log("documentImages:", documentImages);
    if (rule.evidence) {
      const docType = rule.evidence.document_type || "Invoice";
      const pageNum = rule.evidence.page || 1;
      const docPages = documentImages[docType];
      const rawText = documentTexts[docType] || "";
      console.log("Lookup:", docType, "Page:", pageNum, "Pages:", docPages, "RawText Length:", rawText.length);
      
      const imgUrl = docPages && docPages.length > 0 ? (docPages[pageNum - 1] || docPages[0]) : undefined;
      
      setActiveEvidence({
        imageUrl: imgUrl,
        rawText: rawText,
        bbox: rule.evidence.bbox || [0, 0, 0, 0],
        field: rule.rule,
        value: rule.evidence.value || rule.message,
      });
    }
  };

  // ----- DASHBOARD VIEW -----
  if (isDashboardView) {
    const riskScore = calculateRiskScore();
    const totalRules = validationResults.length;
    const passedRules = validationResults.filter(r => r.status === "PASS").length;
    const failedRules = validationResults.filter(r => r.status === "FAIL").length;
    
    return (
      <div className="min-h-screen bg-neutral-950 text-neutral-50 p-6 md:p-12 font-sans selection:bg-blue-500/30">
        <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
          <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-violet-900/10 blur-[120px]" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-900/10 blur-[120px]" />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto space-y-8">
          <button 
            onClick={() => setIsDashboardView(false)}
            className="flex items-center text-neutral-400 hover:text-white transition-colors text-sm font-medium group"
          >
            <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" /> Back to Upload
          </button>

          <header className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-2xl p-8 shadow-2xl">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div>
                <h1 className="text-3xl font-bold text-white mb-2">Validation Dashboard</h1>
                <div className="flex flex-wrap items-center gap-3">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 ring-1 ring-blue-500/20">
                    <Settings2 className="w-3 h-3" />
                    Unified Document Engine
                  </span>
                  {caseSubcategory && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-violet-500/10 text-violet-400 ring-1 ring-violet-500/20">
                      Case Category: {caseSubcategory}
                    </span>
                  )}
                  <span className="text-xs text-neutral-500">
                    Enterprise Engine Controls
                  </span>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-neutral-800/80 rounded-xl p-4 min-w-[130px] border border-neutral-700 shadow-inner">
                  <p className="text-xs text-neutral-400 uppercase font-semibold tracking-wider mb-1">Status</p>
                  <div className={`text-2xl font-bold ${overallStatus === "PASS" ? "text-green-400" : "text-red-400"}`}>
                    {overallStatus}
                  </div>
                </div>
                <div className="bg-neutral-800/80 rounded-xl p-4 min-w-[130px] border border-neutral-700 shadow-inner">
                  <p className="text-xs text-neutral-400 uppercase font-semibold tracking-wider mb-1">Risk Score</p>
                  <div className="flex items-baseline gap-1">
                    <span className={`text-2xl font-bold ${riskScore >= 80 ? "text-green-400" : riskScore >= 50 ? "text-amber-400" : "text-red-400"}`}>
                      {riskScore}
                    </span>
                    <span className="text-sm font-normal text-neutral-500">/100</span>
                  </div>
                </div>
                <div className="bg-neutral-800/80 rounded-xl p-4 min-w-[130px] border border-neutral-700 shadow-inner">
                  <p className="text-xs text-neutral-400 uppercase font-semibold tracking-wider mb-1">Pass Rate</p>
                  <div className="flex items-baseline gap-1 text-2xl font-bold text-blue-400">
                    {passedRules}<span className="text-sm font-normal text-neutral-500">/{totalRules}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <div className="flex justify-between text-xs text-neutral-500 mb-2">
                <span>{passedRules} passed</span>
                <span>{failedRules} failed</span>
              </div>
              <div className="w-full bg-neutral-800 rounded-full h-2 overflow-hidden flex">
                <div 
                  className="bg-gradient-to-r from-green-500 to-green-400 h-2 transition-all duration-700 ease-out" 
                  style={{ width: totalRules > 0 ? `${(passedRules / totalRules) * 100}%` : '0%' }} 
                />
                <div 
                  className="bg-gradient-to-r from-red-500 to-red-400 h-2 transition-all duration-700 ease-out" 
                  style={{ width: totalRules > 0 ? `${(failedRules / totalRules) * 100}%` : '0%' }} 
                />
              </div>
            </div>
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            <div className="space-y-6">
              <section className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-neutral-200 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-neutral-400" />
                  Document Classification Summary
                </h2>
                <div className="space-y-4">
                  {MANDATORY_CATEGORIES.map(category => {
                    const matchedDocs = classifiedDocs.filter(d => d.classification === category);
                    const isMissing = matchedDocs.length === 0;
                    
                    return (
                      <div key={category} className={`p-3 rounded-xl border transition-all ${isMissing ? "border-red-500/20 bg-red-500/5" : "border-green-500/20 bg-green-500/5"}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-sm text-neutral-200">{category}</span>
                          {isMissing ? (
                            <span className="text-xs font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded ring-1 ring-red-500/20">Missing</span>
                          ) : (
                            <span className="text-xs font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded ring-1 ring-green-500/20">{matchedDocs.length} Found</span>
                          )}
                        </div>
                        {!isMissing && (
                          <ul className="space-y-1">
                            {matchedDocs.map((doc, idx) => (
                              <li key={idx} className="text-xs text-neutral-400 flex items-center gap-1.5">
                                <CheckCircle2 className="w-3 h-3 text-green-500" />
                                <span className="truncate">{doc.filename}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    );
                  })}
                  
                  {classifiedDocs.filter(d => !MANDATORY_CATEGORIES.includes(d.classification)).length > 0 && (
                    <div className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-sm text-neutral-200">Other / Unknown</span>
                          <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded ring-1 ring-amber-500/20">Review</span>
                        </div>
                        <ul className="space-y-1">
                          {classifiedDocs.filter(d => !MANDATORY_CATEGORIES.includes(d.classification)).map((doc, idx) => (
                            <li key={idx} className="text-xs text-neutral-400 flex items-center gap-1.5">
                              <AlertCircle className="w-3 h-3 text-amber-500" />
                              <span className="truncate">{doc.filename}</span>
                            </li>
                          ))}
                        </ul>
                    </div>
                  )}
                </div>
              </section>

              <section className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-neutral-200 flex items-center gap-2">
                  <Search className="w-5 h-5 text-neutral-400" />
                  Evidence Viewer
                </h2>
                <p className="text-sm text-neutral-400 mb-4">
                  Click any rule with evidence data to view the extracted field highlighted on the document.
                </p>
                <button 
                  onClick={() => {
                    const docKeys = Object.keys(documentImages);
                    if (docKeys.length > 0) {
                      const docPages = documentImages[docKeys[0]];
                      setActiveEvidence({
                        imageUrl: docPages && docPages.length > 0 ? docPages[0] : "",
                        bbox: [10, 10, 40, 15],
                        field: "Demo Highlight",
                        value: "Example Extraction"
                      });
                    } else {
                      alert("No images processed to view evidence.");
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/20 rounded-xl transition-colors font-medium text-sm"
                >
                  <Search className="w-4 h-4" /> View Sample Extraction
                </button>
              </section>

              <section className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4 text-neutral-200">Group Summary</h2>
                <div className="space-y-3">
                  {Object.entries(GROUP_CONFIG).map(([groupName, config]) => {
                    const groupRules = groupedResults[groupName] || [];
                    const passed = groupRules.filter(r => r.status === "PASS").length;
                    const total = groupRules.length;
                    const allPassed = total > 0 && passed === total;
                    const IconComp = config.icon;
                    
                    return (
                      <button
                        key={groupName}
                        onClick={() => {
                          if (!expandedGroups.has(groupName)) toggleGroup(groupName);
                          document.getElementById(`group-${groupName.replace(/[^a-zA-Z]/g, '')}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all hover:bg-neutral-800/50 ${
                          allPassed ? "border-green-500/20 bg-green-500/5" : "border-red-500/20 bg-red-500/5"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <IconComp className={`w-4 h-4 ${config.color}`} />
                          <span className="text-sm font-medium text-neutral-300">{groupName}</span>
                        </div>
                        <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                          allPassed ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                        }`}>
                          {passed}/{total}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </section>
            </div>

            <div className="lg:col-span-3 space-y-6">
              {Object.entries(GROUP_CONFIG).map(([groupName, config]) => {
                const groupRules = groupedResults[groupName] || [];
                if (groupRules.length === 0) return null;
                
                const isExpanded = expandedGroups.has(groupName);
                const passed = groupRules.filter(r => r.status === "PASS").length;
                const failed = groupRules.filter(r => r.status === "FAIL").length;
                const total = groupRules.length;
                const allPassed = passed === total;
                const IconComp = config.icon;

                return (
                  <section 
                    key={groupName} 
                    id={`group-${groupName.replace(/[^a-zA-Z]/g, '')}`}
                    className="bg-neutral-900/50 border border-neutral-800 rounded-2xl overflow-hidden"
                  >
                    <button
                      onClick={() => toggleGroup(groupName)}
                      className="w-full flex items-center justify-between p-6 hover:bg-neutral-800/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2.5 rounded-xl ${config.bgColor} ${config.borderColor} border`}>
                          <IconComp className={`w-5 h-5 ${config.color}`} />
                        </div>
                        <div className="text-left">
                          <h2 className="text-lg font-semibold text-neutral-200">{groupName}</h2>
                          <p className="text-xs text-neutral-500 mt-0.5">
                            {total} check{total !== 1 ? 's' : ''} • {passed} passed • {failed} failed
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className={`px-3 py-1.5 rounded-lg text-xs font-bold ${
                          allPassed 
                            ? "bg-green-500/10 text-green-400 ring-1 ring-green-500/20" 
                            : "bg-red-500/10 text-red-400 ring-1 ring-red-500/20"
                        }`}>
                          {allPassed ? "ALL PASS" : `${failed} FAIL`}
                        </div>
                        {isExpanded ? <ChevronDown className="w-5 h-5 text-neutral-400" /> : <ChevronRight className="w-5 h-5 text-neutral-400" />}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="px-6 pb-6 space-y-3">
                        <div className="w-full bg-neutral-800 rounded-full h-1.5 overflow-hidden flex mb-4">
                          <div className="bg-green-500 h-1.5 transition-all" style={{ width: `${(passed / total) * 100}%` }} />
                          <div className="bg-red-500 h-1.5 transition-all" style={{ width: `${(failed / total) * 100}%` }} />
                        </div>
                        {groupRules.map((res, idx) => (
                          <div 
                            key={idx}
                            onClick={() => handleRuleClick(res)}
                            className={`p-4 rounded-xl border flex gap-4 transition-all hover:bg-neutral-800/50 ${res.evidence ? 'cursor-pointer' : 'cursor-default'} ${res.status === "PASS" ? "border-green-500/20 bg-green-500/5" : "border-red-500/20 bg-red-500/5"}`}
                          >
                            <div className="mt-0.5 shrink-0">
                              {res.status === "PASS" ? <CheckCircle2 className="w-5 h-5 text-green-400" /> : <AlertCircle className="w-5 h-5 text-red-400" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-1 gap-2">
                                <h3 className="font-semibold text-neutral-200 text-sm">{res.rule}</h3>
                                <div className="flex items-center gap-2 shrink-0">
                                  {res.evidence && (
                                    <span className="text-[10px] font-medium text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full ring-1 ring-blue-500/20">
                                      HAS EVIDENCE
                                    </span>
                                  )}
                                  <span className="text-xs font-mono text-neutral-500 bg-neutral-800 px-2 py-1 rounded">
                                    P{res.priority}
                                  </span>
                                </div>
                              </div>
                              <p className="text-sm text-neutral-400">{res.message}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                );
              })}
            </div>
          </div>
        </div>

        {activeEvidence && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-neutral-900 border border-neutral-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl">
              <div className="flex justify-between items-center p-4 border-b border-neutral-800 bg-neutral-950">
                <h3 className="font-semibold text-neutral-200 flex items-center gap-2">
                  <Search className="w-4 h-4 text-blue-400" /> Evidence Viewer: {activeEvidence.field}
                </h3>
                <button onClick={() => setActiveEvidence(null)} className="text-neutral-400 hover:text-white p-1 transition-colors">
                  <XCircle className="w-6 h-6" />
                </button>
              </div>
              <div className="flex-1 overflow-auto p-4 bg-neutral-900 relative flex justify-center items-center">
                {activeEvidence.imageUrl ? (
                  <div className="relative">
                    <img 
                      src={activeEvidence.imageUrl} 
                      alt="Document Evidence" 
                      className="max-w-full h-auto object-contain shadow-2xl rounded"
                      style={{ maxHeight: '70vh' }}
                    />
                    {activeEvidence.bbox && activeEvidence.bbox.some(val => val > 0) && (
                      <div 
                        className="absolute border-2 border-blue-500 bg-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.5)] animate-pulse rounded-sm"
                        style={{
                          left: `${activeEvidence.bbox[0]}%`,
                          top: `${activeEvidence.bbox[1]}%`,
                          width: `${activeEvidence.bbox[2] - activeEvidence.bbox[0]}%`,
                          height: `${activeEvidence.bbox[3] - activeEvidence.bbox[1]}%`
                        }}
                      />
                    )}
                  </div>
                ) : (
                  <div className="w-full max-w-2xl bg-neutral-950 p-6 rounded-xl border border-neutral-800 font-mono text-xs text-neutral-300 overflow-y-auto max-h-[60vh] whitespace-pre-wrap leading-relaxed">
                    {renderHighlightedText(activeEvidence.rawText || "No text extracted for this document.", activeEvidence.value)}
                  </div>
                )}
              </div>
              <div className="p-4 border-t border-neutral-800 bg-neutral-950 flex justify-between items-center text-sm">
                <div className="text-neutral-400">
                  Extracted Value: <span className="font-mono text-white bg-neutral-800 px-2 py-1 rounded ml-2">{activeEvidence.value}</span>
                </div>
                <div className="text-neutral-500 font-mono text-xs">
                  BBOX: [{activeEvidence.bbox.join(", ")}]
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ----- UPLOAD VIEW -----
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50 p-6 md:p-12 font-sans selection:bg-blue-500/30">
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/20 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-900/20 blur-[120px]" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto space-y-8">
        <header className="space-y-2 text-center flex flex-col items-center mb-12">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-sm font-medium mb-4 ring-1 ring-blue-500/20">
            <Upload className="w-4 h-4" />
            <span>Unified Document Intake</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-neutral-400">
            Verification Portal
          </h1>
          <p className="text-neutral-400 text-lg max-w-2xl">
            Drop all case documents below. The system automatically classifies the 7 mandatory documents and applies unified validation rules.
          </p>
        </header>

        <div className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-8 shadow-2xl">
          <div 
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFilesAdded(Array.from(e.dataTransfer.files));
              }
            }}
            className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
              isDragging ? "border-blue-500 bg-blue-500/5 scale-[1.02]" : "border-neutral-700 hover:border-neutral-500 bg-neutral-950/50"
            }`}
          >
            <div className="flex flex-col items-center gap-4">
              <div className={`p-4 rounded-full ${isDragging ? "bg-blue-500/20 text-blue-400" : "bg-neutral-800 text-neutral-400"}`}>
                <UploadCloud className="w-10 h-10" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-neutral-200 mb-2">Drag and drop documents here</h3>
                <p className="text-neutral-500 text-sm mb-6">Support for PDF, DOCX, XLSX, XLS, CSV, TXT, EML, MSG, PNG, JPG, JPEG, TIF, TIFF files.</p>
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  className="px-6 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-white rounded-xl transition-colors font-medium border border-neutral-700"
                >
                  Browse Files
                </button>
                <input 
                  type="file" 
                  multiple 
                  className="hidden" 
                  ref={fileInputRef}
                  accept=".pdf,.docx,.xlsx,.xls,.csv,.txt,.eml,.msg,.png,.jpg,.jpeg,.tif,.tiff"
                  onChange={(e) => {
                    if (e.target.files) handleFilesAdded(Array.from(e.target.files));
                  }}
                />
              </div>
            </div>
          </div>

          {files.length > 0 && (
            <div className="mt-8 space-y-4">
              <h4 className="text-sm font-semibold text-neutral-400 uppercase tracking-wider">Queued Files ({files.length})</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-2">
                {files.map((file, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-neutral-800/50 rounded-xl border border-neutral-700">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <FileText className="w-5 h-5 text-blue-400 shrink-0" />
                      <div className="truncate">
                        <p className="text-sm font-medium text-neutral-200 truncate">{file.name}</p>
                        <p className="text-xs text-neutral-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                      </div>
                    </div>
                    <button onClick={() => removeFile(idx)} className="text-neutral-500 hover:text-red-400 p-1 transition-colors">
                      <XCircle className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-8 pt-8 border-t border-neutral-800">
            <button
              onClick={handleUpload}
              disabled={isUploading || files.length === 0}
              className={`w-full py-4 px-6 rounded-xl font-medium text-white flex items-center justify-center gap-2 shadow-lg transition-all ${isUploading || files.length === 0 ? "bg-neutral-800 text-neutral-400 cursor-not-allowed" : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500"}`}
            >
              {isUploading ? (
                <>
                  <div className="w-5 h-5 border-2 border-neutral-400 border-t-transparent rounded-full animate-spin" />
                  {uploadProgress}
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-5 h-5" />
                  Submit {files.length} Document{files.length !== 1 ? 's' : ''} for Validation
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
