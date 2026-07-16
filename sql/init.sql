-- ============================================================
-- 枫桥智盾 · 数据库初始化
-- MySQL 8.4 / utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS fengqiao_zhidun
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE fengqiao_zhidun;

-- ============================================================
-- 1. 矛盾纠纷案件主表 (cases)
-- 对接 Excel 导入的 18 列原始字段 + 扩展字段
-- ============================================================
CREATE TABLE cases (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  case_code         VARCHAR(50)    NOT NULL  COMMENT '案件编码/编号',
  agreement_type    VARCHAR(20)    DEFAULT '' COMMENT '协议类型',
  case_source       VARCHAR(60)    DEFAULT '' COMMENT '案件来源',
  mediation_org     VARCHAR(120)   DEFAULT '' COMMENT '调解组织',
  studio            VARCHAR(120)   DEFAULT '' COMMENT '工作室',
  handler           VARCHAR(50)    DEFAULT '' COMMENT '受理人姓名',
  accept_time       DATETIME       DEFAULT NULL COMMENT '受理时间',
  description       TEXT           COMMENT '纠纷简要情况',
  difficulty        VARCHAR(20)    DEFAULT '' COMMENT '案件难度级别',
  dispute_type      VARCHAR(30)    DEFAULT '' COMMENT '纠纷类别/类型',
  case_attr         VARCHAR(30)    DEFAULT '' COMMENT '案件属性',
  special_group     VARCHAR(30)    DEFAULT '' COMMENT '涉及特殊群体情况',
  district          VARCHAR(50)    DEFAULT '' COMMENT '行政划分/乡镇街道',
  has_death         VARCHAR(4)     DEFAULT '' COMMENT '有无死亡',
  mediation_result  VARCHAR(20)    DEFAULT '' COMMENT '调解结果',
  mediation_time    DATETIME       DEFAULT NULL COMMENT '调解时间',
  parties           VARCHAR(500)   DEFAULT '' COMMENT '当事人(逗号分隔)',
  amount            DECIMAL(14,2)  DEFAULT 0.00 COMMENT '调解协议金/涉及金额',

  -- 扩展字段（系统添加）
  import_batch      VARCHAR(32)    DEFAULT '' COMMENT '导入批次号',
  import_time       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
  dedup_status      TINYINT        DEFAULT 0 COMMENT '去重状态: 0=未检测 1=唯一 2=疑似重复 3=已确认重复',
  alert_level       TINYINT        DEFAULT 0 COMMENT '预警等级: 0=无 1=黄 2=橙 3=红',
  status            TINYINT        DEFAULT 0 COMMENT '处置状态: 0=待处置 1=处置中 2=已化解 3=已归档',
  created_at        DATETIME       DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uk_case_code (case_code),
  INDEX idx_district (district),
  INDEX idx_dispute_type (dispute_type),
  INDEX idx_accept_time (accept_time),
  INDEX idx_dedup_status (dedup_status),
  INDEX idx_alert_level (alert_level),
  INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='矛盾纠纷案件主表';

-- ============================================================
-- 2. 去重比对记录表 (dedup_records)
-- 记录每次比对的多维度得分和人工确认
-- ============================================================
CREATE TABLE dedup_records (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  case_id           BIGINT UNSIGNED NOT NULL COMMENT '当前案件ID',
  matched_case_id   BIGINT UNSIGNED NOT NULL COMMENT '匹配到的案件ID',
  score_phone       TINYINT UNSIGNED DEFAULT 0 COMMENT '电话匹配得分 (满分40)',
  score_address     TINYINT UNSIGNED DEFAULT 0 COMMENT '地址匹配得分 (满分30)',
  score_semantic    TINYINT UNSIGNED DEFAULT 0 COMMENT '语义相似度得分 (满分20)',
  score_name        TINYINT UNSIGNED DEFAULT 0 COMMENT '姓名匹配得分 (满分10)',
  total_score       TINYINT UNSIGNED DEFAULT 0 COMMENT '综合评分 (满分100)',
  is_confirmed      TINYINT         DEFAULT 0 COMMENT '人工确认: 0=未确认 1=确认重复 2=判定独立',
  confirmed_by      VARCHAR(50)     DEFAULT '' COMMENT '确认人',
  confirmed_at      DATETIME        DEFAULT NULL COMMENT '确认时间',
  created_at        DATETIME        DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_case_id (case_id),
  INDEX idx_matched_case_id (matched_case_id),
  INDEX idx_total_score (total_score),
  FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY (matched_case_id) REFERENCES cases(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='去重比对记录';

-- ============================================================
-- 3. 预警事件表 (alert_events)
-- 每次触发的预警独立记录
-- ============================================================
CREATE TABLE alert_events (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  case_id           BIGINT UNSIGNED NOT NULL COMMENT '关联案件ID',
  alert_level       TINYINT         NOT NULL COMMENT '预警等级: 1=黄 2=橙 3=红',
  rule_type         VARCHAR(50)     DEFAULT '' COMMENT '触发规则类型',
  channel_count     TINYINT UNSIGNED DEFAULT 0 COMMENT '跨渠道数量',
  channels          VARCHAR(200)    DEFAULT '' COMMENT '关联渠道列表',
  keywords          VARCHAR(300)    DEFAULT '' COMMENT '触发关键词',
  is_pushed         TINYINT         DEFAULT 0 COMMENT '是否已推送: 0=未推送 1=已推送',
  pushed_at         DATETIME        DEFAULT NULL COMMENT '推送时间',
  push_channel      VARCHAR(30)     DEFAULT 'dingtalk' COMMENT '推送渠道',
  handler_dept      VARCHAR(120)    DEFAULT '' COMMENT '责任单位',
  handler_person    VARCHAR(50)     DEFAULT '' COMMENT '责任人',
  resolve_deadline  DATE            DEFAULT NULL COMMENT '处置时限',
  resolved_at       DATETIME        DEFAULT NULL COMMENT '处置完成时间',
  created_at        DATETIME        DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_case_id (case_id),
  INDEX idx_alert_level (alert_level),
  INDEX idx_is_pushed (is_pushed),
  FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='预警事件';

-- ============================================================
-- 4. 重点人员档案表 (person_profiles)
-- 一人一档，全周期管理
-- ============================================================
CREATE TABLE person_profiles (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name              VARCHAR(50)     NOT NULL COMMENT '姓名',
  id_card           VARCHAR(200)    DEFAULT '' COMMENT '身份证号(加密存储)',
  person_type       VARCHAR(50)     NOT NULL COMMENT '人员类型: 精神障碍/刑满释放/社区矫正/吸毒人员等',
  risk_level        TINYINT         DEFAULT 1 COMMENT '风险等级: 1=低 2=中 3=高',
  departments       VARCHAR(200)    DEFAULT '' COMMENT '涉管部门(逗号分隔)',
  district          VARCHAR(50)     DEFAULT '' COMMENT '所属乡镇街道',
  phone             VARCHAR(20)     DEFAULT '' COMMENT '联系电话',
  remark            TEXT            COMMENT '备注',
  status            TINYINT         DEFAULT 1 COMMENT '状态: 1=在管 2=已解管',
  created_at        DATETIME        DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_name (name),
  INDEX idx_person_type (person_type),
  INDEX idx_risk_level (risk_level),
  INDEX idx_district (district)
) ENGINE=InnoDB COMMENT='重点人员档案';

-- ============================================================
-- 5. 随访记录表 (follow_up_records)
-- 关联重点人员，支持周期提醒
-- ============================================================
CREATE TABLE follow_up_records (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  person_id         BIGINT UNSIGNED NOT NULL COMMENT '关联人员ID',
  follow_date       DATE            NOT NULL COMMENT '本次随访日期',
  content           TEXT            COMMENT '随访内容',
  next_date         DATE            DEFAULT NULL COMMENT '下次随访日期',
  is_reminded       TINYINT         DEFAULT 0 COMMENT '是否已到期提醒: 0=未提醒 1=已提醒',
  recorder          VARCHAR(50)     DEFAULT '' COMMENT '记录人',
  created_at        DATETIME        DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_person_id (person_id),
  INDEX idx_next_date (next_date),
  INDEX idx_is_reminded (is_reminded),
  FOREIGN KEY (person_id) REFERENCES person_profiles(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='随访记录';

-- ============================================================
-- 6. 政策法规库表 (policy_library)
-- 支撑政策匹配功能
-- ============================================================
CREATE TABLE policy_library (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  policy_name       VARCHAR(200)    NOT NULL COMMENT '政策名称',
  dept              VARCHAR(60)     DEFAULT '' COMMENT '发布部门',
  category          VARCHAR(50)     DEFAULT '' COMMENT '政策分类',
  target_group      VARCHAR(200)    DEFAULT '' COMMENT '适用对象',
  conditions        TEXT            COMMENT '适用条件',
  benefit_standard  VARCHAR(300)    DEFAULT '' COMMENT '补贴/待遇标准',
  procedure_desc    TEXT            COMMENT '办理流程',
  keywords          VARCHAR(300)    DEFAULT '' COMMENT '检索关键词',
  is_active         TINYINT         DEFAULT 1 COMMENT '是否有效',
  created_at        DATETIME        DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_dept (dept),
  INDEX idx_category (category),
  INDEX idx_is_active (is_active)
) ENGINE=InnoDB COMMENT='政策法规库';

-- ============================================================
-- 7. 操作审计日志表 (audit_logs)
-- 满足"算法可审计、内容可溯源"红线
-- ============================================================
CREATE TABLE audit_logs (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  target_type       VARCHAR(30)     NOT NULL COMMENT '操作目标类型: case/dedup/alert/person/followup',
  target_id         BIGINT UNSIGNED DEFAULT 0 COMMENT '操作目标ID',
  action            VARCHAR(30)     NOT NULL COMMENT '操作: import/dedup/alert/dispatch/resolve/create/update/delete',
  operator          VARCHAR(50)     DEFAULT '' COMMENT '操作人',
  detail            JSON            DEFAULT NULL COMMENT '操作详情(JSON)',
  ip_address        VARCHAR(45)     DEFAULT '' COMMENT '操作IP',
  created_at        DATETIME        DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_target (target_type, target_id),
  INDEX idx_action (action),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='操作审计日志';
