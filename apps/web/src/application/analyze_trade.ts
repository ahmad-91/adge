import type { AnalyzeRequest, AnalyzeResponse } from "@/domain/status";
import type { EngineApiPort } from "@/application/ports/engine_api_port";

export async function analyzeTrade(
  port: EngineApiPort,
  request: AnalyzeRequest
): Promise<AnalyzeResponse> {
  return port.analyze(request);
}
