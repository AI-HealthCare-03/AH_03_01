from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """ml_inference_requests 테이블 신설.

    LangGraph 마이그레이션 계획 3단계 — 비동기 워커 골격 선행. 위험도 예측 ML 호출
    이력·요청 추적용. 현재(P1) 는 그래프 노드가 RiskPredictor 룰 stub 을 동기 호출
    하되 row 등록·결과 저장은 이 테이블을 거친다. 미래 ML 학습 완료 시 ai_worker 의
    위험도 워커가 status=PENDING row 를 BRPOP 큐로 받아 처리하는 패턴으로 전환.

    설계 정렬: 챌린지 인증 워커의 `image_verification_jobs` 테이블과 동일 구조
    (status 인덱스 / 시계열 created_at / job 상태 머신).
    """
    return """
        CREATE TABLE IF NOT EXISTS "ml_inference_requests" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "thread_id" VARCHAR(128),
    "kind" VARCHAR(15) NOT NULL DEFAULT 'RISK_PREDICTION',
    "status" VARCHAR(7) NOT NULL DEFAULT 'PENDING',
    "input_features" JSONB NOT NULL,
    "prediction_result" JSONB,
    "model_version" VARCHAR(40) NOT NULL DEFAULT 'risk-predictor-stub-v0',
    "error_message" TEXT,
    "duration_ms" INTEGER,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "started_at" TIMESTAMPTZ,
    "completed_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_ml_infer_status_created"  ON "ml_inference_requests" ("status", "created_at");
CREATE INDEX IF NOT EXISTS "idx_ml_infer_user_created"    ON "ml_inference_requests" ("user_id", "created_at");
CREATE INDEX IF NOT EXISTS "idx_ml_infer_kind_status"     ON "ml_inference_requests" ("kind", "status");
COMMENT ON COLUMN "ml_inference_requests"."status" IS 'PENDING: PENDING\nRUNNING: RUNNING\nSUCCESS: SUCCESS\nFAILED: FAILED';
COMMENT ON COLUMN "ml_inference_requests"."kind"   IS 'RISK_PREDICTION: RISK_PREDICTION';
COMMENT ON TABLE "ml_inference_requests" IS 'ML 추론 요청·결과 단위 (감사·이력·워커 큐). RiskRecommendationGraph 의 ml_inference 노드가 row 를 생성.';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "ml_inference_requests";
    """
