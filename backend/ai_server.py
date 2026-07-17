"""
枫桥智盾 · AI 语义分析微服务 (gRPC)
=====================================

独立的 AI 分析微服务，通过 gRPC 与主服务通信：
  - ComputeSimilarity：云端/本地 AI 语义相似度计算
  - BatchDedup：批量去重（流式返回进度）
  - GenerateReport：AI 分析报告生成
  - HealthCheck：健康检查

启动：
  python backend/ai_server.py
  默认端口 50051 (gRPC)

架构：
  主服务 (FastAPI :5000) ──gRPC──▶ AI 服务 (:50051)
                                      ├── DeepSeek API
                                      ├── Ollama 本地模型
                                      └── 规则引擎
"""
import os, sys, json, time, grpc, threading
from concurrent import futures

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

import fengqiao_pb2
import fengqiao_pb2_grpc
from models import Case, DedupRecord, get_session, init_db
from ai_service import semantic_similarity, field_scores
from report_generator import generate_report as gen_report
from redis_adapter import get_cache

AI_BACKEND = os.getenv('AI_BACKEND', 'ollama')
VERSION = '2.0.0-ai'


class SemanticServiceImpl(fengqiao_pb2_grpc.SemanticServiceServicer):

    def HealthCheck(self, request, context):
        return fengqiao_pb2.HealthResponse(
            ok=True, backend=AI_BACKEND, version=VERSION
        )

    def ComputeSimilarity(self, request, context):
        score = semantic_similarity(request.text_a, request.text_b)
        return fengqiao_pb2.SimilarityResponse(
            score=score, backend=AI_BACKEND
        )

    def BatchDedup(self, request, context):
        """流式返回去重进度"""
        batch = request.batch
        case_ids = list(request.case_ids)
        if not batch or not case_ids:
            yield fengqiao_pb2.DedupProgress(status='failed', result_json='{"error":"missing batch or case_ids"}')
            return

        session = get_session()
        matches = []
        try:
            new_cases = session.query(Case).filter(Case.import_batch == batch).all()
            total = len(new_cases)

            for idx, new_case in enumerate(new_cases):
                old_cases = session.query(Case).filter(
                    Case.id.notin_([c.id for c in new_cases])
                ).all()

                for old_case in old_cases:
                    a = {c.name: getattr(new_case, c.name) for c in Case.__table__.columns}
                    b = {c.name: getattr(old_case, c.name) for c in Case.__table__.columns}
                    scores = field_scores(a, b)
                    semantic = 0
                    try:
                        a_text = f"{a.get('description','')} {a.get('dispute_type','')}"
                        b_text = f"{b.get('description','')} {b.get('dispute_type','')}"
                        if a_text.strip() and b_text.strip():
                            semantic = max(0, min(20, int(semantic_similarity(a_text, b_text) * 20)))
                    except:
                        pass
                    total_score = scores['phone'] + scores['address'] + semantic + scores['name']
                    if total_score >= 85:
                        session.add(DedupRecord(
                            case_id=new_case.id, matched_case_id=old_case.id,
                            score_phone=scores['phone'], score_address=scores['address'],
                            score_semantic=semantic, score_name=scores['name'], total_score=total_score
                        ))
                        new_case.dedup_status = 2
                        matches.append({'case_id': new_case.id, 'matched': old_case.id, 'score': total_score})

                progress = 10 + int(80 * (idx + 1) / total)
                yield fengqiao_pb2.DedupProgress(
                    progress=progress, status='running', matches=len(matches), total=total
                )

            session.commit()
            yield fengqiao_pb2.DedupProgress(
                progress=100, status='done', matches=len(matches), total=total,
                result_json=json.dumps({'matches': len(matches), 'total': total, 'details': matches[:20]}, ensure_ascii=False)
            )
        except Exception as e:
            session.rollback()
            yield fengqiao_pb2.DedupProgress(status='failed', result_json=json.dumps({'error': str(e)}))
        finally:
            session.close()

    def GenerateReport(self, request, context):
        try:
            result = gen_report(
                report_type=request.report_type,
                year=request.year if request.year else None,
                period=request.period if request.period else None,
            )
            return fengqiao_pb2.ReportResponse(
                success=True,
                report_json=json.dumps(result, ensure_ascii=False)
            )
        except Exception as e:
            return fengqiao_pb2.ReportResponse(success=False, error=str(e))


def serve():
    init_db()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    fengqiao_pb2_grpc.add_SemanticServiceServicer_to_server(SemanticServiceImpl(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print(f'枫桥智盾 AI 微服务已启动 (gRPC :50051) · 后端: {AI_BACKEND}')
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
