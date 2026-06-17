/* =========================================
   홈/출석 관련 API 응답 타입 정의
   백엔드 FastAPI /api/v1/ 엔드포인트 기반
   ========================================= */

/* 내 정보 (GET /api/v1/users/me) */
export interface Me {
  /* USER PK 는 UUID (ERD v1). 문자열 직렬화. */
  id: string;
  email: string;
  name: string;
  nickname?: string | null;
  gender: "MALE" | "FEMALE";
  birth_date?: string;
  birthday?: string;
  phone_number: string;
  avatar_file_id?: number | null;
  avatar_url?: string | null;
  created_at: string;
  is_admin?: boolean;
}

/* 펫 (GET /api/v1/pets/me) */
export interface EquippedBackground {
  id: number;
  name: string;
  gradient?: string | null;
  /** main | sunset | star | beach (이미지 배경 키) */
  image?: string | null;
}

export interface EquippedItemMeta {
  id: number;
  name: string;
  emoji?: string | null;
  slot?: string | null;
  /** head | paws | stage_top | stage_bottom | pet_skin | play */
  placement?: string | null;
  /** 이미지 경로 (/pets/items/*.png) */
  asset?: string | null;
  /** ribbon | flower | ball | butterfly */
  variant?: string | null;
}

export interface MyPet {
  id: number;
  name: string;
  level: number;
  current_xp: number;
  xp_to_next_level: number;
  pet_type?: string;
  selected_style?: string | null;
  hunger?: number;
  cleanliness?: number;
  mood?: number;
  intimacy?: number;
  sick?: boolean;
  equipped_background?: EquippedBackground | null;
  equipped_furniture?: EquippedItemMeta[];
  equipped_decoration?: EquippedItemMeta[];
  created_at: string;
}

/* 챌린지 카테고리 */
export type ChallengeCategory =
  | "EXERCISE"
  | "WATER"
  | "SLEEP"
  | "DIET"
  | "NO_SMOKING"
  | "NO_ALCOHOL"
  | "DISEASE_CARE"
  | "MEDITATION"
  | "WEIGHT_MANAGEMENT";

/* 챌린지 목록(Challenge / ChallengeListResponse / ChallengeStatus)은
   @/types/challenge 가 단일 출처. 중복 정의 시 타입 드리프트로 빌드 실패가 재발. */

/* 질병 타입 */
export type DiseaseType = "HYPERTENSION" | "DIABETES" | "CARDIOVASCULAR";

/* 위험도 등급. 백엔드는 NORMAL/CAUTION/RISK/HIGH_RISK 를 사용하지만
   초기 UI 일부에서 DANGER/HIGH_DANGER 별칭이 쓰여 둘 다 허용 */
export type RiskGrade =
  | "NORMAL"
  | "CAUTION"
  | "RISK"
  | "HIGH_RISK"
  | "DANGER"
  | "HIGH_DANGER";

/* 예측 결과 */
export interface PredictionItem {
  id: number;
  disease_type: DiseaseType;
  risk_score: number;        /* 0-100 */
  risk_grade: RiskGrade;
  risk_factors_count: number;
  created_at: string;
}

/* 예측 목록 응답 */
export interface PredictionListResponse {
  items: PredictionItem[];
}

/* 추천 챌린지 우선순위. 백엔드: TOP|RECOMMENDED|OPTIONAL. 일부 초기 UI 가 사용한
   HIGHEST|SUPPLEMENTAL 별칭도 허용해 점진 마이그레이션 */
export type RecommendationPriority =
  | "TOP"
  | "RECOMMENDED"
  | "OPTIONAL"
  | "HIGHEST"
  | "SUPPLEMENTAL";

/* 추천 챌린지 아이템. 백엔드 응답은 template_id/challenge_id (둘 다 nullable)
   를 사용하며 별도의 id 필드는 없다. reward_points 도 백엔드에 없으므로 옵셔널. */
export interface ChallengeRecommendationItem {
  id?: number;
  template_id?: number | null;
  challenge_id?: number | null;
  title: string;
  description?: string;
  category: ChallengeCategory;
  sub_category?: string | null;
  reason?: string | null;
  priority: RecommendationPriority;
  reward_points?: number;
  already_joined?: boolean;
}

/* 추천 챌린지 목록 응답 */
export interface ChallengeRecommendationResponse {
  items: ChallengeRecommendationItem[];
}

/* 출석 체크 월간 응답 (GET /api/v1/attendance-checks?month=YYYY-MM)
   백엔드는 month_total 을 보내지 않으므로 클라이언트에서 checked_dates.length 로 계산.
   month 필드도 응답에 포함되지만 화면에서 사용하지 않음. */
export interface AttendanceMonthResponse {
  month?: string;
  checked_dates: string[];    /* "YYYY-MM-DD" 배열 */
  current_streak: number;
  next_bonus_at: number | null; /* 다음 보너스 연속 임계 일수 (없으면 null) */
}

/* 출석 체크 POST 응답 (POST /api/v1/attendance-checks) */
export interface AttendanceCheckResponse {
  streak_days: number;
  reward_point: number;
  bonus_point: number;
  transaction_ids: number[];
}

/* 포인트 잔액 (GET /api/v1/points/transactions) */
export type PointTransactionType = "EARN" | "SPEND";
export type PointSource =
  | "CHALLENGE_DAILY"
  | "CHALLENGE_PERIOD"
  | "CHALLENGE_GROUP"
  | "CHALLENGE_WEEKLY_RANK"
  | "ATTENDANCE_DAILY"
  | "ATTENDANCE_BONUS"
  | "QUIZ"
  | "STORE_PURCHASE"
  | "PET_INTERACTION"
  | "REFUND"
  | "ETC";

export interface PointTransaction {
  id: number;
  type?: PointTransactionType;
  amount: number;
  balance_after?: number;
  source?: PointSource;
  source_id?: number | null;
  description: string | null;
  created_at: string;
}

export interface PointBalanceResponse {
  balance: number;
  transactions: PointTransaction[];
}

/* 건강 프로필 아이템 (GET /api/v1/health-records?recordType=profile).
   백엔드 HealthProfileResponse 는 updated_at 을 보내며 record_type 은 응답에 포함되지 않음. */
export interface HealthProfileRecord {
  id?: number;
  record_type?: "profile";
  height_cm?: number;
  weight_kg?: number;
  updated_at?: string;
  recorded_at?: string;
  medications?: string[];
}

/* 측정 통계 시리즈 포인트 */
export interface MetricSeriesPoint {
  recorded_at: string;
  primary_value: number;
  secondary_value?: number;  /* 혈압의 이완기 */
}

/* 측정 통계 응답 (GET /api/v1/health-records/statistics) */
export interface MetricStatResponse {
  metric: string;
  series: MetricSeriesPoint[];
}

/* =========================================
   상점 / 인벤토리 관련 타입
   ========================================= */

export type ItemCategory =
  | "BACKGROUND" | "FURNITURE" | "PET" | "TICKET" | "MEDICINE"
  | "DECORATION" | "FOOD_ANIMAL" | "FOOD_ANIMAL_PREMIUM" | "SNACK_ANIMAL"
  | "FERTILIZER_PLANT" | "FERTILIZER_PLANT_PREMIUM" | "SUPPLEMENT_PLANT" | "WATER";

export type SpeciesLock = "DOG" | "CAT" | "PLANT" | null;

export interface StoreItem {
  id: number;
  category: ItemCategory;
  name: string;
  description?: string | null;
  price: number;
  thumbnail_file_id?: number | null;
  item_metadata: Record<string, unknown>;
  species_lock?: SpeciesLock;
}

export interface StoreItemsResponse { items: StoreItem[]; }

export interface InventoryItem {
  id: number;
  item_id: number;
  category: ItemCategory;
  name: string;
  quantity: number;
  is_equipped: boolean;
  acquired_at: string;
  /** 아이템 썸네일 이미지 경로 (/pets/items/*.png) */
  asset?: string | null;
}

export interface InventoryListResponse { items: InventoryItem[]; }

export interface PurchaseResponse {
  purchase_id: number;
  item_id: number;
  quantity: number;
  point_spent: number;
  point_balance: number;
}

export interface InventoryUseResponse {
  inventory_id: number;
  item_id: number;
  category: ItemCategory;
  remaining_quantity: number;
  pet_id?: number | null;
  sick?: boolean | null;
  hunger?: number | null;
  cleanliness?: number | null;
  mood?: number | null;
  intimacy?: number | null;
  xp_gained?: number | null;
  level?: number | null;
  message: string;
}
