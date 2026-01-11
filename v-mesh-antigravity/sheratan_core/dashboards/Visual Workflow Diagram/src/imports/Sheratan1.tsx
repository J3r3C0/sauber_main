import svgPaths from "./svg-f1bvl3ezp0";
import clsx from "clsx";
type Vector4Props = {
  additionalClassNames?: string;
};

function Vector4({ additionalClassNames = "" }: Vector4Props) {
  return (
    <div className={clsx("absolute", additionalClassNames)}>
      <div className="absolute inset-[-0.75%_-0.35%]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 261.8 121.8">
          <path d={svgPaths.pd0bfff0} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
        </svg>
      </div>
    </div>
  );
}
type Vector3Props = {
  additionalClassNames?: string;
};

function Vector3({ additionalClassNames = "" }: Vector3Props) {
  return (
    <div className={clsx("absolute", additionalClassNames)}>
      <div className="absolute inset-[-1.4%_-0.42%]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 169.4 51.4">
          <path d={svgPaths.p28f4200} fill="var(--fill-0, #0E172A)" id="Vector" stroke="var(--stroke-0, #263551)" strokeWidth="1.4" />
        </svg>
      </div>
    </div>
  );
}
type Vector2Props = {
  additionalClassNames?: string;
};

function Vector2({ additionalClassNames = "" }: Vector2Props) {
  return (
    <div className={clsx("absolute", additionalClassNames)}>
      <div className="absolute inset-[-1.29%_-0.39%]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 231.8 71.8">
          <path d={svgPaths.pb1cb000} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
        </svg>
      </div>
    </div>
  );
}
type Vector1Props = {
  additionalClassNames?: string;
};

function Vector1({ additionalClassNames = "" }: Vector1Props) {
  return (
    <div className={clsx("absolute", additionalClassNames)}>
      <div className="absolute inset-[-1.12%_-0.39%_-1.13%_-0.39%]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 231.8 81.8">
          <path d={svgPaths.p17b4f080} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
        </svg>
      </div>
    </div>
  );
}
type VectorProps = {
  additionalClassNames?: string;
};

function Vector({ additionalClassNames = "" }: VectorProps) {
  return (
    <div className={clsx("absolute", additionalClassNames)}>
      <div className="absolute inset-[-2.5%_-0.45%]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 111 21">
          <path d={svgPaths.p19365880} fill="var(--fill-0, #00C3D4)" fillOpacity="0.12" id="Vector" stroke="var(--stroke-0, #00C3D4)" />
        </svg>
      </div>
    </div>
  );
}
type LanesVectorProps = {
  additionalClassNames?: string;
};

function LanesVector({ additionalClassNames = "" }: LanesVectorProps) {
  return (
    <div className={clsx("absolute", additionalClassNames)}>
      <div className="absolute inset-[-0.5px_0]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1440 1">
          <path d="M0 0.5H1440" id="Vector" stroke="var(--stroke-0, #101827)" />
        </svg>
      </div>
    </div>
  );
}

function Group() {
  return (
    <div className="absolute contents font-['Inter:Regular',sans-serif] font-normal inset-[5.33%_70.25%_89.89%_5%] leading-[normal] not-italic text-[12px] text-nowrap" data-name="Group">
      <p className="absolute inset-[5.33%_79.13%_93%_5%] text-[#e5f4ff]">SHERATAN CORE v1 mdash; RUNTIME FLOW</p>
      <p className="absolute inset-[8.44%_70.25%_89.89%_5%] text-[#9aa4c6]">INTERAKTIVE ÜBERSICHT mdash; VON COCKPIT BIS LLM BACKENDS</p>
    </div>
  );
}

function Lanes() {
  return (
    <div className="absolute contents inset-[13.11%_5%_31.11%_5%]" data-name="lanes">
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[13.11%_89%_85.22%_5%] leading-[normal] not-italic text-[#5e6fa0] text-[12px] text-nowrap">USER / COCKPIT</p>
      <LanesVector additionalClassNames="inset-[15.56%_5%_84.44%_5%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[27.56%_84.38%_70.78%_5%] leading-[normal] not-italic text-[#5e6fa0] text-[12px] text-nowrap">BACKEND ORCHESTRIERUNG</p>
      <LanesVector additionalClassNames="inset-[30%_5%_70%_5%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[46.44%_87.06%_51.89%_5%] leading-[normal] not-italic text-[#5e6fa0] text-[12px] text-nowrap">CORE RUNNER RELAY</p>
      <LanesVector additionalClassNames="inset-[48.89%_5%_51.11%_5%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[66.44%_84.81%_31.89%_5%] leading-[normal] not-italic text-[#5e6fa0] text-[12px] text-nowrap">WORKER, LLM MONITORING</p>
      <LanesVector additionalClassNames="inset-[68.89%_5%_31.11%_5%]" />
    </div>
  );
}

function NodeCockpitUi() {
  return (
    <div className="absolute contents inset-[16.67%_75.75%_73.33%_7.5%]" data-name="node_cockpit_ui">
      <div className="absolute inset-[16.67%_76.25%_73.33%_7.5%]" data-name="Vector">
        <div className="absolute inset-[-1%_-0.35%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 261.8 91.8">
            <path d={svgPaths.p34039f0} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[18.67%_87.75%_79.67%_8.5%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">Cockpit UI</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[21.11%_83.75%_77.22%_8.5%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">React + Vite Frontend</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[23.11%_82.25%_75.22%_8.5%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">backend/cockpit/frontend</p>
      <div className="absolute inset-[18%_77.25%_79.78%_17.5%]" data-name="Vector">
        <div className="absolute inset-[-2.5%_-0.6%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 85 21">
            <path d="M84.5 0.5H0.5V20.5H84.5V0.5Z" fill="var(--fill-0, #00C3D4)" fillOpacity="0.12" id="Vector" stroke="var(--stroke-0, #00C3D4)" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[18.22%_75.75%_80.11%_18.13%] leading-[normal] not-italic text-[#bff8ff] text-[12px] text-nowrap">HTTPS / Browser</p>
    </div>
  );
}

function NodeApiGateway() {
  return (
    <div className="absolute contents inset-[16.67%_52.88%_70%_26.88%]" data-name="node_api_gateway">
      <div className="absolute inset-[16.67%_53.13%_70%_26.88%]" data-name="Vector">
        <div className="absolute inset-[-0.75%_-0.28%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 321.8 121.8">
            <path d={svgPaths.p3801bf10} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[18.67%_61.38%_79.67%_27.88%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">API Gateway Cockpit Backend</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[21.11%_66.06%_77.22%_27.88%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Traefik + FastAPI</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[23.11%_57.94%_75.22%_27.88%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">traefik.yml · main.py · auth.py · routers/*</p>
      <Vector additionalClassNames="inset-[18%_54.38%_79.78%_38.75%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[18.22%_52.88%_80.11%_39.38%] leading-[normal] not-italic text-[#bff8ff] text-[12px] text-nowrap">Ports 80 / 443 / 8088</p>
    </div>
  );
}

function NodeOrchestrator() {
  return (
    <div className="absolute contents inset-[31.11%_31.88%_60%_53.75%]" data-name="node_orchestrator">
      <Vector1 additionalClassNames="inset-[31.11%_31.88%_60%_53.75%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[33.11%_40.87%_65.22%_54.75%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">orchestrator</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[35.33%_35.13%_63%_54.75%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">workflow.js · workflow-run.js</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[37.11%_32.63%_61.22%_54.75%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">Mission-Logik / Routing-Entscheide</p>
    </div>
  );
}

function NodeMemory() {
  return (
    <div className="absolute contents inset-[31.11%_15%_60%_70.63%]" data-name="node_memory">
      <Vector1 additionalClassNames="inset-[31.11%_15%_60%_70.63%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[33.11%_25.44%_65.22%_71.63%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">memory</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[35.33%_23%_63%_71.63%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Redis + Qdrant</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[37.11%_18%_61.22%_71.63%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">session.js · qdrant.js · redis.js</p>
    </div>
  );
}

function NodeGovernance() {
  return (
    <div className="absolute contents inset-[41.11%_31.88%_51.11%_53.75%]" data-name="node_governance">
      <Vector2 additionalClassNames="inset-[41.11%_31.88%_51.11%_53.75%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[42.89%_41.06%_55.44%_54.75%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">governance</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[45.11%_38.75%_53.22%_54.75%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">policy.js · server.js</p>
    </div>
  );
}

function NodeAgentBridge() {
  return (
    <div className="absolute contents inset-[41.11%_15%_51.11%_70.63%]" data-name="node_agent_bridge">
      <Vector2 additionalClassNames="inset-[41.11%_15%_51.11%_70.63%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[42.89%_23.69%_55.44%_71.63%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">agent-bridge</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[45.11%_20.5%_53.22%_71.63%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">chatgpt.js · LLM Proxy</p>
    </div>
  );
}

function NodeOrchestratorCluster() {
  return (
    <div className="absolute contents inset-[23.33%_13.75%_51.11%_52.5%]" data-name="node_orchestrator_cluster">
      <div className="absolute inset-[23.33%_13.75%_54.44%_52.5%]" data-name="Vector">
        <div className="absolute inset-[-0.4%_-0.15%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 541.6 201.6">
            <path d={svgPaths.p272b8200} fill="var(--fill-0, #0B1020)" id="Vector" stroke="var(--stroke-0, #1B2A4A)" strokeWidth="1.6" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[25.56%_37.63%_72.78%_53.75%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">Backend Orchestrierung</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[27.78%_27.94%_70.56%_53.75%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">Node.js Microservices mdash; docker-compose.yml</p>
      <NodeOrchestrator />
      <NodeMemory />
      <NodeGovernance />
      <NodeAgentBridge />
    </div>
  );
}

function Group1() {
  return (
    <div className="absolute contents inset-[52.22%_66%_42.22%_23.5%]" data-name="Group">
      <Vector3 additionalClassNames="inset-[52.22%_66%_42.22%_23.5%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[53.56%_68.88%_44.78%_24.13%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">local_missions.jsonl</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[55.33%_70.63%_43%_24.13%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">Mission Queue</p>
    </div>
  );
}

function Group2() {
  return (
    <div className="absolute contents inset-[52.22%_54.75%_42.22%_34.75%]" data-name="Group">
      <Vector3 additionalClassNames="inset-[52.22%_54.75%_42.22%_34.75%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[53.56%_58.31%_44.78%_35.38%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">local_results.jsonl</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[55.33%_58.38%_43%_35.38%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">Execution Results</p>
    </div>
  );
}

function NodeCoreRunner() {
  return (
    <div className="absolute contents inset-[42.22%_53.75%_40%_22.5%]" data-name="node_core_runner">
      <div className="absolute inset-[42.22%_53.75%_40%_22.5%]" data-name="Vector">
        <div className="absolute inset-[-0.56%_-0.24%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 381.8 161.8">
            <path d={svgPaths.p38788280} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[44.22%_72.06%_54.11%_23.5%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">Core Runner</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[46.67%_67.94%_51.67%_23.5%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Missions API + Executor</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[48.67%_59.44%_49.67%_23.5%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">rest_api.py · missions_runner.py · relay_router.py</p>
      <Group1 />
      <Group2 />
    </div>
  );
}

function NodeRelayHub() {
  return (
    <div className="absolute contents inset-[46.67%_30.5%_37.78%_51.25%]" data-name="node_relay_hub">
      <div className="absolute inset-[46.67%_32.5%_37.78%_51.25%]" data-name="Vector">
        <div className="absolute inset-[-0.64%_-0.35%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 261.8 141.8">
            <path d={svgPaths.p22d4400} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[48.67%_44.13%_49.67%_52.25%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">Relay Hub</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[51.11%_39.56%_47.22%_52.25%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">codder_relay_server.py</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[53.11%_30.5%_45.22%_52.25%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">antigravity_bridge_server.py · browser_worker.py</p>
      <div className="absolute inset-[48%_33.75%_49.78%_58.75%]" data-name="Vector">
        <div className="absolute inset-[-2.5%_-0.42%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 121 21">
            <path d={svgPaths.p400cb60} fill="var(--fill-0, #00C3D4)" fillOpacity="0.12" id="Vector" stroke="var(--stroke-0, #00C3D4)" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[48.22%_33.75%_50.11%_59.38%] leading-[normal] not-italic text-[#bff8ff] text-[12px] text-nowrap">HTTP / JSON Relay</p>
    </div>
  );
}

function Group3() {
  return (
    <div className="absolute contents inset-[56.44%_16.44%_38.67%_72.88%]" data-name="Group">
      <div className="absolute inset-[56.44%_18.38%_38.67%_72.88%]" data-name="Vector">
        <div className="absolute inset-[-1.59%_-0.5%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 141.4 45.4">
            <path d={svgPaths.p2c13800} fill="var(--fill-0, #0E172A)" id="Vector" stroke="var(--stroke-0, #263551)" strokeWidth="1.4" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[57.56%_24.63%_40.78%_73.5%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">core/</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[59.33%_16.44%_39%_73.5%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">llm_client · context_manager</p>
    </div>
  );
}

function Group4() {
  return (
    <div className="absolute contents inset-[56.44%_9.38%_38.67%_82.5%]" data-name="Group">
      <div className="absolute inset-[56.44%_9.38%_38.67%_82.5%]" data-name="Vector">
        <div className="absolute inset-[-1.59%_-0.54%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 131.4 45.4">
            <path d={svgPaths.p2c09b000} fill="var(--fill-0, #0E172A)" id="Vector" stroke="var(--stroke-0, #263551)" strokeWidth="1.4" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[57.56%_15.94%_40.78%_83.13%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">ui/</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[59.33%_10.69%_39%_83.13%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">CustomTkinter UI</p>
    </div>
  );
}

function Group5() {
  return (
    <div className="absolute contents inset-[62.22%_9.38%_32.89%_72.88%]" data-name="Group">
      <div className="absolute inset-[62.22%_9.38%_32.89%_72.88%]" data-name="Vector">
        <div className="absolute inset-[-1.59%_-0.25%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 285.4 45.4">
            <path d={svgPaths.p3f5b1800} fill="var(--fill-0, #0E172A)" id="Vector" stroke="var(--stroke-0, #263551)" strokeWidth="1.4" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[63.33%_14.5%_35%_73.5%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">relay_requests/ · relay_responses/</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[65.11%_16.06%_33.22%_73.5%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">Dateibasierte Kommunikation</p>
    </div>
  );
}

function NodeWorkerCodder() {
  return (
    <div className="absolute contents inset-[47.78%_8.13%_30%_71.88%]" data-name="node_worker_codder">
      <div className="absolute inset-[47.78%_8.13%_30%_71.88%]" data-name="Vector">
        <div className="absolute inset-[-0.45%_-0.28%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 321.8 201.8">
            <path d={svgPaths.p29dfae70} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[49.78%_17.13%_48.56%_72.88%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">Worker: ai_assistent_codder</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[52.22%_16.44%_46.11%_72.88%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">codder_agent.py · core/* · ui/*</p>
      <Group3 />
      <Group4 />
      <Group5 />
    </div>
  );
}

function NodeLlmBackends() {
  return (
    <div className="absolute contents inset-[74.44%_6.25%_12.22%_78.75%]" data-name="node_llm_backends">
      <div className="absolute inset-[74.44%_6.25%_12.22%_78.75%]" data-name="Vector">
        <div className="absolute inset-[-0.75%_-0.37%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 241.8 121.8">
            <path d={svgPaths.p3e83e580} fill="var(--fill-0, #070B16)" id="Vector" stroke="var(--stroke-0, #1C3250)" strokeWidth="1.8" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[76.44%_15.06%_21.89%_79.75%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">LLM Backends</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[78.89%_10.38%_19.44%_79.75%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">OpenAI · Ollama · llama-cpp</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[80.89%_9.63%_17.44%_79.75%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">Konfig: .env · requirements.txt</p>
    </div>
  );
}

function NodeMonitoring() {
  return (
    <div className="absolute contents inset-[74.44%_51.13%_12.22%_32.5%]" data-name="node_monitoring">
      <Vector4 additionalClassNames="inset-[74.44%_51.25%_12.22%_32.5%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[76.44%_62.69%_21.89%_33.5%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">Monitoring</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[78.89%_58.5%_19.44%_33.5%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Prometheus + Grafana</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[80.89%_51.25%_17.44%_33.5%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">prometheus.yml · grafana-dashboards.json</p>
      <Vector additionalClassNames="inset-[75.78%_52.5%_22%_40.63%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[76%_51.13%_22.33%_41.25%] leading-[normal] not-italic text-[#bff8ff] text-[12px] text-nowrap">Metrics / Dashboards</p>
    </div>
  );
}

function NodeRootConfig() {
  return (
    <div className="absolute contents inset-[74.44%_71.25%_12.22%_12.5%]" data-name="node_root_config">
      <Vector4 additionalClassNames="inset-[74.44%_71.25%_12.22%_12.5%]" />
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[76.44%_81.56%_21.89%_13.5%] leading-[normal] not-italic text-[#e5f4ff] text-[12px] text-nowrap">{`Root & Config`}</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[78.89%_75.88%_19.44%_13.5%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">core_config.json · start_all.ps1</p>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[80.89%_74.94%_17.44%_13.5%] leading-[normal] not-italic text-[#7b86ae] text-[12px] text-nowrap">Zentrale Ports / Pfade / Services</p>
    </div>
  );
}

export default function Sheratan() {
  return (
    <div className="relative size-full" data-name="sheratan 1">
      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1600 900">
        <path d="M1600 0H0V900H1600V0Z" fill="url(#paint0_linear_5_310)" id="Vector" />
        <defs>
          <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_5_310" x1="0" x2="769.139" y1="0" y2="1367.36">
            <stop stopColor="#050814" />
            <stop offset="0.4" stopColor="#050814" />
            <stop offset="1" stopColor="#050814" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-[-57.78%_17.5%_42.22%_17.5%]" data-name="Vector">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1040 1040">
          <path d={svgPaths.pa141fc0} fill="url(#paint0_radial_5_332)" id="Vector" />
          <defs>
            <radialGradient cx="0" cy="0" gradientTransform="translate(52000 5200) scale(62400)" gradientUnits="userSpaceOnUse" id="paint0_radial_5_332" r="1">
              <stop stopColor="#00C3D4" stopOpacity="0.4" />
              <stop offset="0.35" stopColor="#00C3D4" stopOpacity="0.12" />
              <stop offset="1" stopColor="#00C3D4" stopOpacity="0" />
            </radialGradient>
          </defs>
        </svg>
      </div>
      <div className="absolute inset-[10%_27.5%]" data-name="Vector">
        <div className="absolute inset-[-0.1%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 721.4 721.4">
            <path d={svgPaths.p17424d00} id="Vector" opacity="0.7" stroke="var(--stroke-0, #123248)" strokeDasharray="6 6" strokeWidth="1.4" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[21.11%_33.75%]" data-name="Vector">
        <div className="absolute inset-[-0.13%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 521.4 521.4">
            <path d={svgPaths.p30b47600} id="Vector" opacity="0.7" stroke="var(--stroke-0, #123248)" strokeDasharray="3 12" strokeWidth="1.4" />
          </svg>
        </div>
      </div>
      <Group />
      <Lanes />
      <NodeCockpitUi />
      <NodeApiGateway />
      <NodeOrchestratorCluster />
      <NodeCoreRunner />
      <NodeRelayHub />
      <NodeWorkerCodder />
      <NodeLlmBackends />
      <NodeMonitoring />
      <NodeRootConfig />
      <div className="absolute inset-[21.67%_73.13%_78.33%_23.75%]" data-name="Vector">
        <div className="absolute inset-[-1.05px_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 50 2.1">
            <path d="M0 1.05H50" id="Vector" stroke="var(--stroke-0, #00C3D4)" strokeWidth="2.1" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[19.22%_73.13%_79.11%_24.38%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">HTTPS</p>
      <div className="absolute inset-[21.67%_47.5%_73.89%_46.88%]" data-name="Vector">
        <div className="absolute inset-[-2.4%_-0.47%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 90.8529 41.919">
            <path d={svgPaths.pe8741f0} id="Vector" stroke="var(--stroke-0, #00C3D4)" strokeWidth="2.1" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[22%_44.56%_76.33%_48.75%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Mission / Workflow</p>
      <div className="absolute inset-[34.44%_29.38%_65.56%_63.75%]" data-name="Vector">
        <div className="absolute inset-[-0.75px_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 110 1.5">
            <path d="M0 0.75H110" id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[32%_29.44%_66.33%_64.75%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Vektor / Session</p>
      <div className="absolute inset-[36.67%_40.63%_58.33%_58.13%]" data-name="Vector">
        <div className="absolute inset-[-0.68%_-3.43%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.3707 45.6092">
            <path d={svgPaths.p4cc0240} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[38.22%_39%_60.11%_56.38%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Policy Check</p>
      <div className="absolute inset-[36.67%_22.5%_58.33%_70%]" data-name="Vector">
        <div className="absolute inset-[-1.56%_-0.22%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 120.527 46.4045">
            <path d={svgPaths.p235ef240} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[38.22%_20%_60.11%_72.5%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">High-Level LLM Calls</p>
      <div className="absolute inset-[30%_63.13%_57.78%_34.38%]" data-name="Vector">
        <div className="absolute inset-[-0.33%_-2.47%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 41.9736 110.718">
            <path d={svgPaths.p27d80600} id="Vector" stroke="var(--stroke-0, #00C3D4)" strokeWidth="2.1" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[35.33%_61.56%_63%_34.38%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">HTTP 8088</p>
      <div className="absolute bottom-1/2 left-[46.25%] right-[48.75%] top-[47.78%]" data-name="Vector">
        <div className="absolute inset-[-3.64%_-0.23%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 80.3638 21.4552">
            <path d={svgPaths.p2c1c6580} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[48%_46.94%_50.33%_47.88%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">relay_router.py</p>
      <div className="absolute inset-[53.33%_28.13%_45.56%_67.5%]" data-name="Vector">
        <div className="absolute inset-[-7.42%_-0.15%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 70.2121 11.4849">
            <path d={svgPaths.p1b8af780} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[50.89%_27.69%_47.44%_68.13%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">JSON Relay</p>
      <div className="absolute inset-[70%_15%_25.56%_81.88%]" data-name="Vector">
        <div className="absolute inset-[-1.46%_-0.94%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 50.937 41.1713">
            <path d={svgPaths.p36b28fc0} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[70.89%_13.13%_27.44%_82.5%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">llm_client.py</p>
      <div className="absolute inset-[60%_61.88%_25.56%_34.38%]" data-name="Vector">
        <div className="absolute inset-[-0.24%_-1.13%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 61.3619 130.629">
            <path d={svgPaths.p85cca80} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[60.89%_59.94%_37.44%_35%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Metrics / Logs</p>
      <div className="absolute inset-[45.56%_45%_25.56%_40.63%]" data-name="Vector">
        <div className="absolute inset-[-0.19%_-0.24%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 231.124 260.994">
            <path d={svgPaths.p29f7ed80} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[30%_66.25%_25.56%_28.75%]" data-name="Vector">
        <div className="absolute inset-[-0.04%_-0.92%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 81.4709 400.294">
            <path d={svgPaths.p2d921280} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[51.11%_65.63%_18.89%_28.75%]" data-name="Vector">
        <div className="absolute inset-[-0.09%_-0.79%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 91.423 270.474">
            <path d={svgPaths.p15536c00} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[57.78%_27.5%_16.67%_28.75%]" data-name="Vector">
        <div className="absolute inset-[-0.31%_-0.03%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 700.468 231.425">
            <path d={svgPaths.pba6e000} id="Vector" stroke="var(--stroke-0, #2E8099)" strokeDasharray="5 4" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal inset-[75.33%_65.56%_23%_29.75%] leading-[normal] not-italic text-[#9aa4c6] text-[12px] text-nowrap">Ports / Pfade</p>
    </div>
  );
}