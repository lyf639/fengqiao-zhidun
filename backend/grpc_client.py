"""
枫桥智盾 · gRPC 客户端
=======================

主服务通过此模块调用 AI 微服务，封装为简单函数接口。
连接失败时自动回退到本地直接调用（本地模式）。

使用：
  from grpc_client import ai_similarity, ai_dedup, ai_report, ai_health
"""
import os, json, grpc
import fengqiao_pb2
import fengqiao_pb2_grpc

GRPC_HOST = os.getenv('GRPC_AI_HOST', 'localhost')
GRPC_PORT = os.getenv('GRPC_AI_PORT', '50051')
GRPC_TIMEOUT = int(os.getenv('GRPC_TIMEOUT', '120'))

_channel = None
_stub = None


def _get_stub():
    global _channel, _stub
    if _stub is None:
        try:
            _channel = grpc.insecure_channel(f'{GRPC_HOST}:{GRPC_PORT}')
            _stub = fengqiao_pb2_grpc.SemanticServiceStub(_channel)
        except Exception:
            return None
    return _stub


def ai_similarity(text_a: str, text_b: str) -> dict:
    """调用 AI 微服务计算语义相似度，失败回退到本地"""
    stub = _get_stub()
    if stub:
        try:
            req = fengqiao_pb2.SimilarityRequest(text_a=text_a, text_b=text_b)
            resp = stub.ComputeSimilarity(req, timeout=GRPC_TIMEOUT)
            return {'score': resp.score, 'backend': resp.backend}
        except Exception:
            pass
    # 回退到本地直接调用
    from ai_service import semantic_similarity
    return {'score': semantic_similarity(text_a, text_b), 'backend': 'local_fallback'}


def ai_dedup(batch: str, case_ids: list, progress_callback=None) -> dict:
    """调用 AI 微服务流式去重，progress_callback(progress, matches) 接收进度"""
    stub = _get_stub()
    if stub:
        try:
            req = fengqiao_pb2.DedupRequest(case_ids=case_ids, batch=batch)
            result = {'matches': 0, 'total': 0}
            for evt in stub.BatchDedup(req, timeout=GRPC_TIMEOUT * 2):
                if evt.status == 'done':
                    if evt.result_json:
                        result = json.loads(evt.result_json)
                    break
                elif evt.status == 'failed':
                    return {'error': 'dedup_failed', 'matches': 0}
                if progress_callback:
                    progress_callback(evt.progress, evt.matches)
            return result
        except Exception:
            pass

    # 回退：本地执行
    from tasks import task_dedup_batch
    return task_dedup_batch({'batch': batch, 'case_ids': case_ids}, 'local')


def ai_report(report_type: str, year: int = None, period: int = None) -> dict:
    """调用 AI 微服务生成报告"""
    stub = _get_stub()
    if stub:
        try:
            req = fengqiao_pb2.ReportRequest(report_type=report_type, year=year or 0, period=period or 0)
            resp = stub.GenerateReport(req, timeout=GRPC_TIMEOUT)
            if resp.success:
                return json.loads(resp.report_json)
            return {'error': resp.error}
        except Exception as e:
            pass

    from report_generator import generate_report
    return generate_report(period=report_type, year=year)


def ai_health() -> dict:
    """AI 微服务健康检查"""
    stub = _get_stub()
    if stub:
        try:
            resp = stub.HealthCheck(fengqiao_pb2.HealthRequest(), timeout=5)
            return {'ok': resp.ok, 'backend': resp.backend, 'version': resp.version}
        except Exception:
            pass
    return {'ok': False, 'error': 'unreachable'}


def ai_parse_text(text: str) -> dict:
    """调用 AI 微服务解析文字为结构化字段"""
    stub = _get_stub()
    if stub:
        try:
            req = fengqiao_pb2.ParseTextRequest(text=text)
            resp = stub.ParseText(req, timeout=GRPC_TIMEOUT)
            return {
                'fields': json.loads(resp.fields_json) if resp.fields_json else {},
                'confidence': resp.confidence,
                'backend': resp.backend,
                'error': resp.error,
            }
        except Exception:
            pass
    from ai_service import parse_case_text
    return parse_case_text(text)
