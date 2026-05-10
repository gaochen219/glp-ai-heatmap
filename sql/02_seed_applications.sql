-- ═══════════════════════════════════════════════════════════════════
-- GLP AI 应用指挥中心 — 68 应用 seed
-- 先执行 01_schema.sql 建表，再执行本文件
-- dept_idx: 0 Asset · 1 IDC · 2 新能源 · 3 基金/其他 · 4 财务 · 5 HR · 6 Legal/IA/PR
-- ═══════════════════════════════════════════════════════════════════

DELETE FROM dim_applications;

-- ─── 整体 General · AI Buddy 2.0 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, is_hot, display_order) VALUES
('AI 智能助理',        'general', '集团通用', 0, 'high', 1, 1),
('制度流程助理',       'general', '集团通用', 0, 'high', 0, 2),
('资讯热点推送',       'general', '集团通用', 0, 'high', 0, 3),
('个人知识库',         'general', '集团通用', 1, 'high', 0, 4),
('团队知识库',         'general', '集团通用', 3, 'high', 0, 5),
('GLP AI 文档翻译',    'general', '集团通用', 4, 'high', 0, 6),
('GLP AI 文稿校对',    'general', '集团通用', 5, 'high', 0, 7),
('GLP AI PPT 助手',    'general', '集团通用', 6, 'high', 0, 8);

-- ─── 应用 · 管理决策 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('AI 智能问数',        'application', '管理决策', 0, 'high', 1),
('决策辅助系统',       'application', '管理决策', 2, 'mid',  2),
('隐山-投资 Memo',     'application', '管理决策', 3, 'mid',  3),
('税金分析助手',       'application', '管理决策', 4, 'high', 4),
('Legal-案例库',       'application', '管理决策', 6, 'mid',  5),
('IA-检查点校验',      'application', '管理决策', 6, 'mid',  6);

-- ─── 应用 · 创新赋能 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('AI 数字化营销',       'application', '创新赋能', 0, 'mid',  1),
('AI&普笈客户管理',     'application', '创新赋能', 0, 'mid',  2),
('e 园区',              'application', '创新赋能', 0, 'mid',  3),
('AI 找仓',             'application', '创新赋能', 0, 'mid',  4),
('消防监控识别',        'application', '创新赋能', 2, 'mid',  5),
('运营月报自动化',      'application', '创新赋能', 2, 'mid',  6),
('组件清洗分析',        'application', '创新赋能', 2, 'mid',  7),
('基金-贷款合同识别',   'application', '创新赋能', 3, 'mid',  8),
('财务汇率自动化',      'application', '创新赋能', 4, 'high', 9),
('财务回单自动整理校验','application', '创新赋能', 4, 'high', 10),
('文档智能搜索',        'application', '创新赋能', 5, 'mid',  11),
('IA-内审翻译',         'application', '创新赋能', 6, 'high', 12),
('PR-舆情翻译',         'application', '创新赋能', 6, 'high', 13),
('PR-文案自审查',       'application', '创新赋能', 6, 'mid',  14),
('PR-智能素材库',       'application', '创新赋能', 6, 'mid',  15);

-- ─── 应用 · 流程自动化 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('租赁合同/滞纳金',     'application', '流程自动化', 0, 'high', 1),
('园区进退场提醒',      'application', '流程自动化', 0, 'mid',  2),
('财务数据自动化',      'application', '流程自动化', 0, 'high', 3),
('DC base 智能巡检',    'application', '流程自动化', 1, 'high', 4),
('新能源业财合同识别',  'application', '流程自动化', 2, 'mid',  5),
('SAP/PTP 智能提单',    'application', '流程自动化', 4, 'high', 6),
('PTP 运维合同识别',    'application', '流程自动化', 4, 'high', 7),
('档案自动查重',        'application', '流程自动化', 5, 'mid',  8),
('人事信息识别分类',    'application', '流程自动化', 5, 'mid',  9);

-- ─── 应用 · 行业资讯 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('竞对市场周报',        'application', '行业资讯', 0, 'high', 1),
('竞对分析',            'application', '行业资讯', 0, 'high', 2),
('客户洞察',            'application', '行业资讯', 0, 'mid',  3),
('IDC 市场周报',        'application', '行业资讯', 1, 'high', 4),
('每周资讯',            'application', '行业资讯', 2, 'mid',  5),
('热点观察',            'application', '行业资讯', 2, 'mid',  6),
('深度联想',            'application', '行业资讯', 2, 'mid',  7),
('基金-宏观经济季报',   'application', '行业资讯', 3, 'mid',  8),
('PR-舆情 Newsletter',  'application', '行业资讯', 6, 'high', 9);

-- ─── 应用 · 业务系统 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('小普 AI 助手',        'application', '业务系统', 0, 'high', 1),
('IDC 运维事件分析',    'application', '业务系统', 1, 'high', 2),
('集中式光伏运维助手',  'application', '业务系统', 2, 'high', 3),
('SAP/PTP 系统助手',    'application', '业务系统', 4, 'high', 4),
('CPM/HFM 系统助手',    'application', '业务系统', 4, 'high', 5),
('绩效系统数字人',      'application', '业务系统', 5, 'mid',  6);

-- ─── 应用 · 业务知识库 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('小普/APM/CMS/BI 知识库','application','业务知识库',0, 'high', 1),
('IDC 知识库',           'application','业务知识库', 1, 'high', 2),
('运维知识库',           'application','业务知识库', 2, 'high', 3),
('运营故障知识库',       'application','业务知识库', 2, 'mid',  4),
('SAP/PTP 知识库',       'application','业务知识库', 4, 'high', 5),
('CPM/HFM 知识库',       'application','业务知识库', 4, 'high', 6),
('档案图书馆',           'application','业务知识库', 5, 'mid',  7);

-- ─── 基础建设 · 安全 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('AI 安全身份认证',      'foundation', '安全', 0, 'high', 1),
('漏洞报告自动化',       'foundation', '安全', 0, 'high', 2),
('安全事件报告助手',     'foundation', '安全', 1, 'mid',  3),
('AI 安全护栏',          'foundation', '安全', 3, 'high', 4),
('AI 权限管理',          'foundation', '安全', 4, 'high', 5),
('AI 安全 Newsletter',   'foundation', '安全', 6, 'mid',  6);

-- ─── 基础建设 · 治理 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('AI 大模型合规治理',    'foundation', '治理', 0, 'high', 1),
('第三方风险评估',       'foundation', '治理', 3, 'mid',  2),
('ITPM Chatbot',         'foundation', '治理', 5, 'mid',  3);

-- ─── 基础建设 · 研发 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('AI 中台',              'foundation', '研发', 0, 'high', 1),
('AI 大模型评估/审计',   'foundation', '研发', 2, 'high', 2),
('LLM 选型更新机制',     'foundation', '研发', 4, 'mid',  3),
('运维 AI 自动化',       'foundation', '研发', 6, 'mid',  4);

-- ─── 基础建设 · 数据 ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('AI 数据基建 Foundry',  'foundation', '数据', 0, 'high', 1),
('AI Newsletter',        'foundation', '数据', 2, 'high', 2),
('多模态数据获取',       'foundation', '数据', 4, 'mid',  3);

-- ─── 新项目 Pipeline ───
INSERT INTO dim_applications (name, section, subsection, dept_idx, complexity, display_order) VALUES
('OpenClaw 数字员工',    'pipeline', '规划中', 0, 'planned', 1),
('GEO 品牌排序',         'pipeline', '规划中', 0, 'planned', 2),
('AI 监盘',              'pipeline', '规划中', 2, 'planned', 3),
('财务预算归因',         'pipeline', '规划中', 4, 'planned', 4);

-- ─── 平台总人数（示例，等 ai-all-pers 接口通了用 upsert）───
INSERT OR REPLACE INTO dim_platforms (company_descr, pers_cnt) VALUES
('资产平台', 527),
('IDC',      480),
('新能源',   320),
('基金/其他',180),
('财务',     210),
('HR',        95),
('Legal/IA/PR', 60);

-- ─── 校验 ───
SELECT section, COUNT(*) AS n, SUM(CASE WHEN complexity='high' THEN 1 ELSE 0 END) AS high,
       SUM(CASE WHEN complexity='mid' THEN 1 ELSE 0 END) AS mid,
       SUM(CASE WHEN complexity='planned' THEN 1 ELSE 0 END) AS planned
FROM dim_applications
GROUP BY section
ORDER BY CASE section WHEN 'general' THEN 1 WHEN 'application' THEN 2
                      WHEN 'foundation' THEN 3 ELSE 4 END;
