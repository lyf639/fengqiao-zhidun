-- MySQL dump 10.13  Distrib 8.4.9, for Win64 (x86_64)
--
-- Host: localhost    Database: fengqiao_zhidun
-- ------------------------------------------------------
-- Server version	8.4.9

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `fengqiao_zhidun`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `fengqiao_zhidun` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `fengqiao_zhidun`;

--
-- Table structure for table `alert_events`
--

DROP TABLE IF EXISTS `alert_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_events` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `case_id` bigint unsigned NOT NULL COMMENT '???????',
  `alert_level` tinyint NOT NULL COMMENT 'Ԥ???ȼ?: 1=?? 2=?? 3=?',
  `rule_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???????????',
  `channel_count` tinyint unsigned DEFAULT '0' COMMENT '???????',
  `channels` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?????????б',
  `keywords` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?????ؼ',
  `is_pushed` tinyint DEFAULT '0' COMMENT '?Ƿ???????: 0=δ???? 1=?????',
  `pushed_at` datetime DEFAULT NULL COMMENT '????ʱ?',
  `push_channel` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT 'dingtalk' COMMENT '?????',
  `handler_dept` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???ε?λ',
  `handler_person` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?????',
  `resolve_deadline` date DEFAULT NULL COMMENT '????ʱ?',
  `resolved_at` datetime DEFAULT NULL COMMENT '????????ʱ?',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_case_id` (`case_id`),
  KEY `idx_alert_level` (`alert_level`),
  KEY `idx_is_pushed` (`is_pushed`),
  CONSTRAINT `alert_events_ibfk_1` FOREIGN KEY (`case_id`) REFERENCES `cases` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Ԥ???¼';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alert_events`
--

LOCK TABLES `alert_events` WRITE;
/*!40000 ALTER TABLE `alert_events` DISABLE KEYS */;
INSERT INTO `alert_events` VALUES (1,37,2,'medium_amount',1,'当事人申请 (线上)','民间借贷纠纷',0,NULL,'dingtalk','','',NULL,NULL,'2026-07-17 02:49:24'),(2,31,2,'medium_amount',1,'当事人申请(线下)','民间借贷纠纷',0,NULL,'dingtalk','','',NULL,NULL,'2026-07-17 02:49:24'),(3,28,3,'high_amount',1,'当事人申请(线下)','其他劳动争议纠纷',0,NULL,'dingtalk','','',NULL,NULL,'2026-07-17 02:49:24'),(4,24,2,'medium_amount',1,'当事人申请(线下)','损害赔偿纠纷',0,NULL,'dingtalk','','',NULL,NULL,'2026-07-17 02:49:24'),(5,23,3,'high_amount',1,'当事人申请(线下)','损害赔偿纠纷',0,NULL,'dingtalk','','',NULL,NULL,'2026-07-17 02:49:24'),(6,21,3,'high_amount',1,'当事人申请(线下)','损害赔偿纠纷',0,NULL,'dingtalk','','',NULL,NULL,'2026-07-17 02:49:24'),(7,20,2,'medium_amount',1,'当事人申请(线下)','邻里纠纷',0,NULL,'dingtalk','','',NULL,NULL,'2026-07-17 02:49:24'),(8,16,1,'difficulty_level',1,'当事人申请(线下)','邻里纠纷',0,NULL,'dingtalk','','',NULL,NULL,'2026-07-17 02:49:24');
/*!40000 ALTER TABLE `alert_events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `target_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '????Ŀ??????: case/dedup/alert/person/followup',
  `target_id` bigint unsigned DEFAULT '0' COMMENT '????Ŀ??ID',
  `action` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '????: import/dedup/alert/dispatch/resolve/create/update/delete',
  `operator` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???',
  `detail` json DEFAULT NULL COMMENT '????????(JSON)',
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_target` (`target_type`,`target_id`),
  KEY `idx_action` (`action`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='??????????־';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_logs`
--

LOCK TABLES `audit_logs` WRITE;
/*!40000 ALTER TABLE `audit_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `audit_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `case_tag_relations`
--

DROP TABLE IF EXISTS `case_tag_relations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `case_tag_relations` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `case_id` bigint unsigned NOT NULL,
  `tag_id` bigint unsigned NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_case_tag` (`case_id`,`tag_id`),
  KEY `idx_relation_case` (`case_id`),
  KEY `idx_relation_tag` (`tag_id`),
  CONSTRAINT `case_tag_relations_ibfk_1` FOREIGN KEY (`case_id`) REFERENCES `cases` (`id`) ON DELETE CASCADE,
  CONSTRAINT `case_tag_relations_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `case_tags` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='案件-标签关联';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `case_tag_relations`
--

LOCK TABLES `case_tag_relations` WRITE;
/*!40000 ALTER TABLE `case_tag_relations` DISABLE KEYS */;
/*!40000 ALTER TABLE `case_tag_relations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `case_tags`
--

DROP TABLE IF EXISTS `case_tags`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `case_tags` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `color` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT '#2A5290',
  `tag_category` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `description` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_tag_category` (`tag_category`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='案件标签表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `case_tags`
--

LOCK TABLES `case_tags` WRITE;
/*!40000 ALTER TABLE `case_tags` DISABLE KEYS */;
INSERT INTO `case_tags` VALUES (1,'高风险','#C41E3A','风险','','2026-07-16 22:07:14'),(2,'中风险','#E67E22','风险','','2026-07-16 22:07:14'),(3,'低风险','#27AE60','风险','','2026-07-16 22:07:14'),(4,'涉特殊人群','#8E44AD','人群','','2026-07-16 22:07:14'),(5,'涉渔业','#16A085','区域','','2026-07-16 22:07:14'),(6,'积案','#7F8C8D','时效','','2026-07-16 22:07:14'),(7,'群体性','#E74C3C','风险','','2026-07-16 22:07:14'),(8,'涉未成年人','#3498DB','人群','','2026-07-16 22:07:14'),(9,'已化解','#27AE60','状态','','2026-07-16 22:07:14');
/*!40000 ALTER TABLE `case_tags` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cases`
--

DROP TABLE IF EXISTS `cases`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cases` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `case_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '????????/???',
  `agreement_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT 'Э?????',
  `case_source` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '??????Դ',
  `mediation_org` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '??????֯',
  `studio` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???',
  `handler` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?????????',
  `accept_time` datetime DEFAULT NULL COMMENT '????ʱ?',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '???׼?Ҫ???',
  `difficulty` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?????Ѷȼ??',
  `dispute_type` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '????????/???',
  `case_attr` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?????',
  `special_group` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?漰????Ⱥ?????',
  `district` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '????????/?????ֵ?',
  `has_death` varchar(4) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???????',
  `mediation_result` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???????',
  `mediation_time` datetime DEFAULT NULL COMMENT '????ʱ?',
  `parties` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '??????(???ŷָ',
  `amount` decimal(14,2) DEFAULT '0.00' COMMENT '????Э????/?漰?',
  `import_batch` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???????κ',
  `import_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '????ʱ?',
  `dedup_status` tinyint DEFAULT '0' COMMENT 'ȥ??״̬: 0=δ???? 1=Ψһ 2=?????ظ? 3=??ȷ???ظ?',
  `alert_level` tinyint DEFAULT '0' COMMENT 'Ԥ???ȼ?: 0=?? 1=?? 2=?? 3=?',
  `status` tinyint DEFAULT '0' COMMENT '????״̬: 0=?????? 1=?????? 2=?ѻ??? 3=?ѹ鵵',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_case_code` (`case_code`),
  KEY `idx_district` (`district`),
  KEY `idx_dispute_type` (`dispute_type`),
  KEY `idx_accept_time` (`accept_time`),
  KEY `idx_dedup_status` (`dedup_status`),
  KEY `idx_alert_level` (`alert_level`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=43 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ì?ܾ??װ????';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cases`
--

LOCK TABLES `cases` WRITE;
/*!40000 ALTER TABLE `cases` DISABLE KEYS */;
INSERT INTO `cases` VALUES (1,'DS001','','12345??','','','',NULL,'???????????','','????','','','???','','',NULL,'??,??',5000.00,'20260716231436_e6c353a0','2026-07-16 23:14:37',2,0,0,'2026-07-16 23:14:37','2026-07-17 02:48:28'),(2,'DS002','','?????','','','',NULL,'???????????????????','','????','','','???','','',NULL,'??,??',3000.00,'20260716231436_e6c353a0','2026-07-16 23:14:37',3,0,0,'2026-07-16 23:14:37','2026-07-16 23:36:04'),(3,'ST001','','12345??','','','',NULL,'???????????','','????','','','???','','',NULL,'??,??',5000.00,'20260716233133_4fcfdeec','2026-07-16 23:31:34',0,0,0,'2026-07-16 23:31:34','2026-07-16 23:31:34'),(4,'ST002','','?????','','','',NULL,'???????????????????','','????','','','???','','',NULL,'??,??',3000.00,'20260716233133_4fcfdeec','2026-07-16 23:31:34',0,0,0,'2026-07-16 23:31:34','2026-07-16 23:31:34'),(5,'ST01','','12345','','','',NULL,'????','','????','','','???','','',NULL,'A,B',5000.00,'20260716233324_00606481','2026-07-16 23:33:24',0,0,0,'2026-07-16 23:33:24','2026-07-16 23:33:24'),(6,'ST02','','??','','','',NULL,'??????????','','????','','','???','','',NULL,'A,C',3000.00,'20260716233324_00606481','2026-07-16 23:33:24',0,0,0,'2026-07-16 23:33:24','2026-07-16 23:33:24'),(7,'L01','','12345','','','',NULL,'漏水发霉','','邻里纠纷','','','菜园镇','','',NULL,'A,B',5000.00,'20260716233426_5938557a','2026-07-16 23:34:27',0,0,0,'2026-07-16 23:34:27','2026-07-16 23:34:27'),(8,'L02','','网格','','','',NULL,'楼上漏水发霉要求赔偿','','邻里纠纷','','','菜园镇','','',NULL,'A,C',3000.00,'20260716233426_5938557a','2026-07-16 23:34:27',0,0,0,'2026-07-16 23:34:27','2026-07-16 23:34:27'),(9,'FRESH1','','12345','','','',NULL,'卫生间漏水发霉','','邻里纠纷','','','菜园镇','','',NULL,'张,李',5000.00,'20260716233645_94b7b749','2026-07-16 23:36:46',2,0,0,'2026-07-16 23:36:46','2026-07-16 23:48:13'),(10,'FRESH2','','网格','','','',NULL,'楼上卫生间漏水导致楼下墙体发霉墙皮脱落要求赔偿','','邻里纠纷','','','菜园镇','','',NULL,'张,王',3000.00,'20260716233645_94b7b749','2026-07-16 23:36:46',2,0,0,'2026-07-16 23:36:46','2026-07-16 23:48:21'),(11,'R01','','12345热线','','','','2026-06-15 00:00:00','','','邻里纠纷','','','菜园镇','','',NULL,'张,李',1500.00,'20260717000732_1f631954','2026-07-17 00:07:32',0,0,0,'2026-07-17 00:07:32','2026-07-17 00:07:32'),(12,'R02','','公安接警','','','','2026-06-20 00:00:00','','','损害赔偿','','','枸杞乡','','',NULL,'王,赵',250000.00,'20260717000732_1f631954','2026-07-17 00:07:32',0,0,0,'2026-07-17 00:07:32','2026-07-17 00:07:32'),(13,'R03','','信访平台','','','','2026-06-10 00:00:00','','','征地拆迁','','','嵊山镇','','',NULL,'陈,周',80000.00,'20260717000732_1f631954','2026-07-17 00:07:32',0,0,0,'2026-07-17 00:07:32','2026-07-17 00:07:32'),(14,'R04','','网格员上报','','','','2026-06-22 00:00:00','','','邻里纠纷','','','菜园镇','','',NULL,'刘,孙',3000.00,'20260717000732_1f631954','2026-07-17 00:07:32',0,0,0,'2026-07-17 00:07:32','2026-07-17 00:07:32'),(15,'R05','','12345热线','','','','2026-06-05 00:00:00','','','劳动争议','','','洋山镇','','',NULL,'吴,郑',15000.00,'20260717000732_1f631954','2026-07-17 00:07:32',0,0,0,'2026-07-17 00:07:32','2026-07-17 00:07:32'),(16,'ZJ090400220260520000004','书面协议','当事人申请(线下)','菜园镇东海社区人民调解委员会','阿拉娘家人调解工作室','孙丹妮','2026-05-20 14:23:15','蒋飞箭与商盼盼为上下楼关系，蒋飞箭家住浙江省嵊泗县菜园镇董家弄16号号202室，商盼盼家住浙江省嵊泗县菜园镇董家弄16号302室，商盼盼家卫生间漏水，导致蒋飞箭家窗户、柜子腐烂，墙壁部分区域发霉。双方关于赔偿问题于2026年5月20日共同向菜园镇东海社区人民调解委员会申请调解。','一般纠纷','邻里纠纷','无','不涉及','菜园镇','否','调解成功','2026-05-20 15:09:26','蒋飞箭,商盼盼',1500.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,1,0,'2026-07-17 02:47:06','2026-07-17 02:49:24'),(17,'ZJ090400220260518000003','口头协议','当事人申请(线下)','菜园镇东海社区人民调解委员会','阿拉娘家人调解工作室','孙丹妮','2026-05-18 08:20:00','鲁彩味住蓬山园4幢6号102室，朱梅芳住蓬山园5幢7号101室。双方为邻里关系，鲁彩味近期清晨起床较早，晨时家庭成员交谈、居家活动等产生的声音较大。长期持续噪音影响朱梅芳的睡眠。双方产生矛盾，向我社区提出申请调解。','简单纠纷','邻里纠纷','无','','菜园镇','否','调解成功','2026-05-18 16:20:41','鲁彩味,朱梅芳',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:48:27'),(18,'ZJ090400220260519000001','书面协议','当事人申请(线下)','菜园镇青沙村人民调解委员会','','沈琼','2026-05-18 15:48:46','当事人周腰红与周国强因其母亲王月定老人的赡养责任分担、身后事务安排及遗产处置问题发生纠纷。','简单纠纷','婚姻家庭纠纷','无','不涉及','菜园镇','否','调解成功','2026-05-18 15:58:43','周腰红,周国强',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',1,0,0,'2026-07-17 02:47:06','2026-07-17 02:48:20'),(19,'ZJ090400220260529000001','书面协议','当事人申请(线下)','菜园镇人民调解委员会','','应佳蓉','2026-05-29 09:22:16','申请人林生龙与被申请人林兵系父子关系，  2026年5月28日，两人因赡养费发生纠纷。经了解，林生龙年老体弱，劳动能力衰退，无充足稳定经济来源，基本生活难以自给，其子林兵担忧赡养款项无法用于林生龙基本生活开支、被违规挥霍的考量，擅自中止履行赡养义务，双方因此产生实质性民事争议，引发本次赡养纠纷，向菜园镇人民调解委员会申请调解。','简单纠纷','其他纠纷','无','不涉及','菜园镇','否','调解成功','2026-05-29 09:27:11','林生龙,林兵',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',1,0,0,'2026-07-17 02:47:06','2026-07-17 02:48:20'),(20,'ZJ090400220260527000002','书面协议','当事人申请(线下)','菜园镇人民调解委员会','','应佳蓉','2026-05-26 09:19:49','2026年5月26日，申请人赵智敏所居住一楼的房屋出现渗水，主要来源于2楼卫生间水管老化，双方就漏水原因、责任归属、修复方案及费用承担等问题多次沟通，但未达到一致意见 ，向菜园镇人民调解委员会申请调解。','一般纠纷','邻里纠纷','无','不涉及','菜园镇','否','调解成功','2026-05-26 13:25:23','王国华,赵智敏',10000.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,2,0,'2026-07-17 02:47:06','2026-07-17 02:49:24'),(21,'ZJ090400720260611000001','书面协议','当事人申请(线下)','枸杞乡东昇村人民调解委员会','','吴燕','2026-06-03 09:00:00','2025年11月，何松康在渔船干活时因故致左大腿及左手受伤，何松康要求张岳军进行赔偿。','简单纠纷','损害赔偿纠纷','无','不涉及','枸杞乡','否','调解成功','2026-06-03 10:00:00','何松康,张岳军',230000.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,3,0,'2026-07-17 02:47:06','2026-07-17 02:49:24'),(22,'ZJ090400720260615000001','书面协议','当事人申请(线下)','枸杞乡人民调解委员会','','汤飞龙','2026-06-11 08:30:00','海鲜一条街三家店面由于地下水管破裂导致产生4800元水费，三家租户和房东因水费如何分摊产生纠纷，故向调委会提出调解。','简单纠纷','损害赔偿纠纷','无','不涉及','枸杞乡','否','调解成功','2026-06-11 10:00:00','王朋才,张荣旋,蔡国明,童洁',4800.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:48:08'),(23,'ZJ090400720260530000001','书面协议','当事人申请(线下)','枸杞乡人民调解委员会','','汤飞龙','2026-05-29 08:30:00','王建双于2012年入股浙嵊渔07210号船，占六股里的半股，2025年9月25日下午16点左右，浙嵊渔07210号船在152海区生产作业，王建双在收网时被起网机缆绳缠住摔倒，导致左腿受伤，后因大动脉流血过多而截肢，经上海市第六人民医院住院治疗，目前伤情基本稳定，船老大张仕江已支付全部医疗费用，2026年上半年工资已支付，现经宁波三益司法鉴定所司法鉴定，构成五级伤残，双方因后续赔偿问题产生纠纷。','一般纠纷','损害赔偿纠纷','无','不涉及','枸杞乡','否','调解成功','2026-05-30 08:30:00','王建双,张仕江',1030000.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,3,0,'2026-07-17 02:47:06','2026-07-17 02:49:24'),(24,'ZJ090400720260529000001','书面协议','当事人申请(线下)','枸杞乡人民调解委员会','','汤飞龙','2026-05-19 09:00:00','2025年10月，马必进因被渔网勾倒后受伤，马必进要求朱存云进行赔偿。','简单纠纷','损害赔偿纠纷','无','不涉及','枸杞乡','否','调解成功','2026-05-19 09:30:00','马必进,朱存云',18000.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,2,0,'2026-07-17 02:47:06','2026-07-17 02:49:24'),(25,'ZJ090400820260612000001','口头协议','当事人申请(线下)','花鸟乡人民调解委员会','','任金权','2026-06-10 08:55:37','市政公司下属某水厂关闭了供水阀门，导致附近渔民的水塘无法正常进水或补水，直接影响水产养殖。遂双方发生矛盾，申请调委会调解。','简单纠纷','邻里纠纷','无','','花鸟乡','否','调解成功','2026-06-12 08:54:41','张仲祥,嵊泗县花鸟岛市政管理服务有限公司',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',1,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:55'),(26,'ZJ090400620260612000001','口头协议','当事人申请(线下)','黄龙乡人民调解委员会','','罗珠芬','2026-06-11 15:30:07','林松祥家养的鸡被狗咬死了两只，要求张恺赔偿损失，张恺以狗不是其饲养为由拒绝赔偿，两人协商无果申请调委会调解。','简单纠纷','邻里纠纷','无','','黄龙乡','否','调解成功','2026-06-12 16:13:52','林松祥,张恺',300.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:55'),(27,'ZJ090400620260520000001','口头协议','调委会主动调解','黄龙乡人民调解委员会','','罗珠芬','2026-05-16 09:09:19','刘春菊去奚舟平的食品店购买零食，回家后想起来是店家少找了零钱，又折回去找补，奚舟平回答找的零食是准确的，于是因此两人互补相让起了争执。','简单纠纷','邻里纠纷','无','','黄龙乡','否','调解成功','2026-05-16 09:26:38','奚舟平,刘春菊',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:52'),(28,'ZJ090400620260519000005','口头协议','当事人申请(线下)','黄龙乡峙岙村人民调解委员会','','陈儿','2026-05-18 14:44:11','鲁永跃因在毛科军的船上干活时被缆绳夹伤左手。造成左小指、无名指截指手术，双方因后续赔偿问题发生纠纷，申请村调委会调解。','简单纠纷','其他劳动争议纠纷','无','','黄龙乡','否','调解成功','2026-05-19 14:42:57','鲁永跃,毛科军',149834.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',1,3,0,'2026-07-17 02:47:06','2026-07-17 02:49:24'),(29,'ZJ090400620260519000004','口头协议','调委会主动调解','黄龙乡峙岙村人民调解委员会','','陈儿','2026-05-13 14:23:46','袁爱芳家楼上的烟囱被徐松祥家装网络的网线给固定缠住，担心烟囱断裂要求其拆掉，徐不愿意，两人引起争执，调委会主动介入调解。','简单纠纷','邻里纠纷','无','','黄龙乡','否','调解成功','2026-05-19 14:23:27','袁爱芳,徐松祥',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:49'),(30,'ZJ090400320260527000001','口头协议','当事人申请 (线上)','嵊山镇陈钱山村人民调解委员会','','王芬','2026-05-25 15:52:10','居住在三角弄2号居民赖和存反映说他家左侧门前过道（陈钱山路15号商品房）悬挂空调数量较多（5台空调外机）空调外机热风造成居民生活不便，要求村调解；','简单纠纷','邻里纠纷','无','','嵊山镇','否','调解成功','2026-05-25 15:56:15','赖和存,秦婷婷',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',1,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:46'),(31,'ZJ090400320260529000001','书面协议','当事人申请(线下)','嵊山镇人民调解委员会','','许红','2026-05-22 15:59:52','何洁与孔芦斌是男女朋友关系，现已分手。在交往期间孔芦斌在2025年3月5日起陆续向何洁借款合计25000元，后经何洁多次讨要拒不归还。双方就此发生纠纷。','简单纠纷','民间借贷纠纷','无','涉及妇女儿童纠纷','嵊山镇','否','调解成功','2026-05-28 16:17:43','何洁,孔芦斌',25000.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',1,2,0,'2026-07-17 02:47:06','2026-07-17 02:49:24'),(32,'ZJ090400520260609000001','口头协议','当事人申请(线下)','五龙乡会城村人民调解委员会','','张雨晴','2026-06-08 09:10:15','村民鲍秋菊与杨宗庆因菜地浇水引发口角，情绪激动。经调解，双方消除分歧，握手言和，邻里重归和睦。','简单纠纷','邻里纠纷','无','','五龙乡','否','调解成功','2026-06-09 10:09:37','杨宗庆,鲍秋菊',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:46'),(33,'ZJ090400520260514000001','口头协议','当事人申请(线下)','五龙乡会城村人民调解委员会','','张雨晴','2026-05-13 08:33:52','临近六一假期，村里开展共富集市摊位抽签仪式，王冬根与陈水芬因意见不合发生争执。经调解，双方达成谅解，握手言和，矛盾顺利化解。','简单纠纷','邻里纠纷','无','','五龙乡','否','调解成功','2026-05-14 13:33:43','王冬根,陈水芬',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:45'),(34,'ZJ090400420260529000004','口头协议','当事人申请(线下)','洋山镇城东社区人民调解委员会','','朱阿平','2026-05-26 09:09:47','因位于东平巷57号刘汉定家房后的树木枝叶茂盛，大风一来容易吹倒，影响周边居民。','简单纠纷','邻里纠纷','无','','洋山镇','否','调解成功','2026-05-26 09:35:12','刘汉定,刘汉福',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:44'),(35,'ZJ090400420260529000003','口头协议','当事人申请(线下)','洋山镇城东社区人民调解委员会','','朱阿平','2026-05-20 08:30:50','因道路施工人员在位于东平巷139号毛跃军家旁进行道路施工，水沟太窄，一到下大雨，水就流不急。影响了毛跃军家。','简单纠纷','其他纠纷','无','','洋山镇','否','调解成功','2026-05-20 09:03:19','毛跃军,夏金五',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:39'),(36,'ZJ090400420260529000002','口头协议','当事人申请(线下)','洋山镇城东社区人民调解委员会','','朱阿平','2026-05-14 08:45:53','因位于东新路75号刘世伦家的化粪池管子没有直接接到水沟，深入到屋后的空地上，引起恶臭，影响了位于东新路71的费善章家及周边居民。','简单纠纷','邻里纠纷','无','','洋山镇','否','调解成功','2026-05-14 08:58:25','费善章,刘世伦',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:36'),(37,'ZJ090400420260526000007','书面协议','当事人申请 (线上)','洋山镇人民调解委员会','洋山阿伯调解工作室','林小英','2026-05-21 10:41:43','经了解，2010年左右，刘玉菊向陈信南借款2万元，此后刘玉菊陆续归还2200元，还欠本金17800元未还。2023年6月2日，刘玉菊重新向陈信南出具借条，载明刘玉菊借陈信南17800元。现要求刘玉菊立即归还借款本金17800元。','一般纠纷','民间借贷纠纷','无','不涉及','洋山镇','否','调解成功','2026-05-21 15:10:26','陈信南,刘玉菊',17800.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',1,2,0,'2026-07-17 02:47:06','2026-07-17 02:49:24'),(38,'ZJ090400420260612000001','口头协议','当事人申请(线下)','洋山镇圣港社区人民调解委员会','','毛三军','2026-06-03 08:31:43','社区居民林令忠向社区居委会反映，居民陈央儿在自家房屋东面屋角的公共街巷路面上，私自放置一块圆锥形路障。该区域为辖区公共通行小街小巷，属于公共通行区域，陈央儿私自设置路障的行为，擅自占用公共通行路面，遮挡通行视线、挤占通行空间，对过往居民、行人日常出行造成极大不便，存在通行安全隐患，邻里双方因此产生矛盾。社区工作人员接到诉求后，第一时间前往现场核查情况，确认居民反映问题属实。\n调解过程：工作人员组织双方当事人到场开展调解工作。首先向陈央儿普及市容及公共道路管理相关规定，明确辖区小街小巷公共路面属于公共通行设施，归公众共同使用，任何个人不得私自占用、圈占、设置障碍物，不得影响公共通行秩序。同时耐心告知其私自放置路障存在的安全隐患，以及该行为对周边居民日常出行造成的不良影响。\n经工作人员耐心沟通、情理结合的劝导教育，陈央儿充分认识到自身行为的不当之处，知晓私自占用公共街巷路面、设置通行障碍物违反公共通行管理规定，且损害了公共利益及邻里权益。陈央儿当场表示积极配合社区工作，愿意立即整改，移除违规放置的圆锥形路障。\n同时，工作人员对双方进行邻里和睦宣讲，引导双方换位思考、互帮互助，自觉遵守公共街巷通行秩序，杜绝私自占用公共路面、影响邻里通行的行为，共同维护辖区通畅、和谐的居住通行环境。林令忠对陈央儿的整改态度表示认可，双方无争议、无矛盾。','简单纠纷','邻里纠纷','无','','洋山镇','否','调解成功','2026-06-03 08:50:31','林令忠,陈央儿',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:30'),(39,'ZJ090400420260526000006','口头协议','当事人申请(线下)','洋山镇圣港社区人民调解委员会','','毛三军','2026-05-21 08:45:26','近日，辖区居民邵红向社区部潘洁反映诉求，称沙田弄路段公共污水管道出现破裂故障，管道内污水持续外溢，大量污水淤积在路面地面。污水不仅散发刺鼻异味，严重影响周边空气质量，且路面污水积水、脏乱湿滑，对居民日常出行造成极大不便，同时存在滋生蚊虫、影响环境卫生及道路通行安全的隐患，希望社区能够尽快介入处理。\n社区干部在接到居民反映后，第一时间响应群众诉求，秉持快速处置、为民解忧的工作原则，即刻前往沙田弄现场进行实地核查。经现场勘查确认，该路段公共污水管道接口破损、管道堵塞，导致污水无法正常流通进而外溢路面，属实影响周边居民正常生活。\n为高效解决问题，社区工作人员立即对接专业管道维修疏通人员，详细说明现场故障情况，安排维修人员携带专业设备赶赴现场开展抢修作业。维修人员抵达现场后，迅速排查管道堵塞点位与破损位置，通过专业疏通设备清理管道内淤积的杂物、淤泥，对破裂的管道接口进行规整、修复，彻底疏通堵塞管道，恢复污水正常流通。整个维修疏通过程规范有序，社区工作人员全程现场跟进、监督施工进度，及时协调解决施工过程中出现的问题，确保维修工作高效推进。\n经过现场专业处置，外溢的污水逐步回流排出，路面淤积污水全部清理干净，沙田弄污水管道排水功能彻底恢复正常，路面环境卫生恢复整洁，彻底消除了污水外溢带来的各类隐患。此次问题处置全程高效、闭环落地，及时解决了居民的急难愁盼问题，有效化解了因设施故障引发的民生困扰，未引发邻里矛盾及后续纠纷。','简单纠纷','其他纠纷','无','','洋山镇','否','调解成功','2026-05-21 09:05:12','邵红,潘洁',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:25'),(40,'ZJ090400420260526000005','口头协议','当事人申请(线下)','洋山镇圣港社区人民调解委员会','','毛三军','2026-05-18 08:36:57','2026年5月18日，辖区居民毛其军主动向社区干部毛三军反映，钥匙路路段窨井出现堵塞问题，引发污水倒流，污水漫溢至自家屋内，对居家环境造成污染，同时产生异味，严重影响日常生活起居，希望社区能够尽快协调处理。\n接到居民诉求后，社区工作人员高度重视，第一时间响应群众诉求，即刻前往现场进行实地核查。经现场查看，钥匙路该路段窨井因长期堆积落叶、泥沙、生活垃圾等杂物，造成管道严重堵塞，雨水和生活污水无法正常排放，进而出现污水倒灌、漫流的情况，确实对毛其军居民的居住环境造成较大影响。\n为快速解决群众难题，社区干部立即联系专业管道疏通工人赶赴现场开展抢修疏通工作。施工过程中，社区干部全程跟进监督，配合管道工清理窨井内淤积的杂物、疏通地下堵塞管道，彻底清除管道内堵塞源头，保障排水通道通畅。经过专业作业处理，该路段窨井排水功能全面恢复，污水倒流、漫溢问题彻底解决，现场积水逐步排净，周边环境恢复整洁。\n处置完成后，社区干部当场与居民毛其军进行沟通反馈，详细说明问题成因及处置结果，耐心解答居民疑问，告知其后续管道排水已恢复正常，不会再出现污水倒流问题。居民现场对社区快速响应、高效处置的工作态度和处置结果表示认可，此次邻里民生问题圆满化解，无后续争议与纠纷。','简单纠纷','其他纠纷','无','','洋山镇','否','调解成功','2026-05-18 08:48:45','毛其军,毛三军',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:21'),(41,'ZJ090400420260526000003','口头协议','当事人申请(线下)','洋山镇圣港社区人民调解委员会','','毛三军','2026-05-16 13:22:41','社区接到辖区居民邱和国反映，丰渔弄路段因居民陈玉飞家出水管道堵塞，排水不畅导致积水倒灌，对邱和国的居住环境造成不良影响，日常出行、房屋周边卫生均受到干扰。邱和国希望社区能够介入协调处理，彻底解决管道堵塞积水问题，消除对自家生活的影响。\n社区工作人员接到居民诉求后，第一时间秉持公平公正、为民解忧的工作原则，前往丰渔弄现场核查实际情况。工作人员实地查看后确认，积水源头为陈玉飞家外接出水管道，该管道因长期堆积杂物、淤泥造成堵塞，陈玉飞家日常出水无法正常排入公共管网，积水外溢流淌至丰渔弄路面，进而蔓延至邱和国房屋周边，确实对邱和国的正常生活造成了实质性影响。\n为快速化解邻里矛盾、解决民生问题，社区工作人员当即联系专业管道疏通维修人员到场处置。维修人员抵达现场后，对堵塞的出水管道进行全面排查，精准定位堵塞点位，通过专业设备清理管道内淤积的淤泥、杂物，彻底疏通堵塞管道，恢复管道正常排水功能。经过专业施工，丰渔弄路面积水逐步排空，管道排水通畅，现场环境恢复整洁。\n管道维修处置完成后，社区工作人员随即组织双方当事人进行现场调解。调解过程中，工作人员耐心向陈玉飞说明管道堵塞引发积水、影响邻里生活的实际情况，普及邻里相处互帮互助、维护公共居住环境的相关理念。','简单纠纷','邻里纠纷','无','','洋山镇','否','调解成功','2026-05-16 13:40:15','陈玉飞,邱和国',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:18'),(42,'ZJ090400420260526000004','口头协议','当事人申请(线下)','洋山镇雄洋社区人民调解委员会','','陈芳军','2026-05-15 08:25:22','住在小区里的瞿某把家里淘汰的一个旧鞋柜放在自家门外的拐角处，上面还堆着杂物。对门的刘某，有一次晚上下楼碰到杂物。刘某提了几次，瞿某家口头答应，但东西就是不见少，还说“就放自家门口，又不占你家地”。刘某一气之下，把杂物挪到了对方门口，矛盾彻底激化。\n社区得知情况后，立马到现场调解，给当事人双方播放居民楼火灾逃生的科普视频，特别指出楼道堆物是堵塞“生命通道”。经社区耐心调解，瞿某家意识到自身问题，立即清理了自己堆放的杂物。','简单纠纷','邻里纠纷','无','','洋山镇','否','调解成功','2026-05-15 08:29:11','刘海兵,翟纪朋',0.00,'20260717024706_275a8eb6','2026-07-17 02:47:06',2,0,0,'2026-07-17 02:47:06','2026-07-17 02:47:13');
/*!40000 ALTER TABLE `cases` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `category_mappings`
--

DROP TABLE IF EXISTS `category_mappings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `category_mappings` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `source_system` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_category` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_category` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `confidence` float DEFAULT '1',
  `is_auto` tinyint DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_source_category` (`source_system`,`source_category`),
  KEY `idx_source_system` (`source_system`),
  KEY `idx_target_category` (`target_category`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类映射表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `category_mappings`
--

LOCK TABLES `category_mappings` WRITE;
/*!40000 ALTER TABLE `category_mappings` DISABLE KEYS */;
INSERT INTO `category_mappings` VALUES (1,'12345热线','邻里矛盾','邻里纠纷',1,1,'2026-07-16 22:07:14'),(2,'12345热线','消费投诉','消费维权',1,1,'2026-07-16 22:07:14'),(3,'公安接警','打架斗殴','邻里纠纷',1,1,'2026-07-16 22:07:14'),(4,'公安接警','家暴','家庭暴力',1,1,'2026-07-16 22:07:14'),(5,'信访平台','征地补偿','征地拆迁',1,1,'2026-07-16 22:07:14'),(6,'信访平台','房屋征收','征地拆迁',1,1,'2026-07-16 22:07:14'),(7,'网格员上报','楼上漏水','物业矛盾',1,1,'2026-07-16 22:07:14'),(8,'网格员上报','噪音扰民','邻里纠纷',1,1,'2026-07-16 22:07:14');
/*!40000 ALTER TABLE `category_mappings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dedup_records`
--

DROP TABLE IF EXISTS `dedup_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dedup_records` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `case_id` bigint unsigned NOT NULL COMMENT '??ǰ???',
  `matched_case_id` bigint unsigned NOT NULL COMMENT 'ƥ?䵽?İ??',
  `score_phone` tinyint unsigned DEFAULT '0' COMMENT '?绰ƥ???÷? (????40)',
  `score_address` tinyint unsigned DEFAULT '0' COMMENT '??ַƥ???÷? (????30)',
  `score_semantic` tinyint unsigned DEFAULT '0' COMMENT '???????ƶȵ÷? (????20)',
  `score_name` tinyint unsigned DEFAULT '0' COMMENT '????ƥ???÷? (????10)',
  `total_score` tinyint unsigned DEFAULT '0' COMMENT '?ۺ????? (????100)',
  `is_confirmed` tinyint DEFAULT '0' COMMENT '?˹?ȷ??: 0=δȷ?? 1=ȷ???ظ? 2=?ж?????',
  `confirmed_by` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT 'ȷ???',
  `confirmed_at` datetime DEFAULT NULL COMMENT 'ȷ??ʱ?',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_case_id` (`case_id`),
  KEY `idx_matched_case_id` (`matched_case_id`),
  KEY `idx_total_score` (`total_score`),
  CONSTRAINT `dedup_records_ibfk_1` FOREIGN KEY (`case_id`) REFERENCES `cases` (`id`) ON DELETE CASCADE,
  CONSTRAINT `dedup_records_ibfk_2` FOREIGN KEY (`matched_case_id`) REFERENCES `cases` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=80 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ȥ?رȶԼ?¼';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dedup_records`
--

LOCK TABLES `dedup_records` WRITE;
/*!40000 ALTER TABLE `dedup_records` DISABLE KEYS */;
INSERT INTO `dedup_records` VALUES (1,1,2,35,28,0,8,71,0,'',NULL,'2026-07-16 23:14:40'),(2,2,1,35,28,0,8,71,0,'',NULL,'2026-07-16 23:14:40'),(3,10,7,35,28,17,8,88,0,'',NULL,'2026-07-16 23:36:59'),(4,10,8,35,28,17,8,88,0,'',NULL,'2026-07-16 23:36:59'),(5,10,9,35,28,17,8,88,0,'',NULL,'2026-07-16 23:36:59'),(6,9,7,35,28,17,8,88,0,'',NULL,'2026-07-16 23:36:59'),(7,9,8,35,28,17,8,88,0,'',NULL,'2026-07-16 23:36:59'),(8,9,10,35,28,17,8,88,0,'',NULL,'2026-07-16 23:36:59'),(9,9,7,35,28,18,8,89,0,'',NULL,'2026-07-16 23:48:22'),(10,9,8,35,28,18,8,89,0,'',NULL,'2026-07-16 23:48:22'),(11,9,10,35,28,18,8,89,0,'',NULL,'2026-07-16 23:48:22'),(12,10,7,35,28,18,8,89,0,'',NULL,'2026-07-16 23:48:22'),(13,10,8,35,28,20,8,91,0,'',NULL,'2026-07-16 23:48:22'),(14,10,9,35,28,18,8,89,0,'',NULL,'2026-07-16 23:48:22'),(15,1,3,15,30,0,10,55,0,'',NULL,'2026-07-17 02:48:28'),(16,1,4,15,30,0,10,55,0,'',NULL,'2026-07-17 02:48:28'),(17,1,5,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:28'),(18,1,6,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:28'),(19,42,34,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(20,42,36,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(21,42,38,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(22,42,41,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(23,41,34,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(24,41,36,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(25,41,38,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(26,41,42,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(27,40,35,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(28,40,39,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(29,39,35,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(30,39,40,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(31,38,34,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(32,38,36,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(33,38,41,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(34,38,42,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(35,36,34,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(36,36,38,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(37,36,41,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(38,36,42,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(39,35,39,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(40,35,40,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(41,34,36,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(42,34,38,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(43,34,41,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(44,34,42,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(45,33,32,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(46,32,33,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(47,29,26,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(48,29,27,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(49,27,26,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(50,27,29,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(51,26,27,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(52,26,29,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(53,24,21,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(54,24,22,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(55,24,23,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(56,23,21,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(57,23,22,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(58,23,24,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(59,22,21,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(60,22,23,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(61,22,24,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(62,21,22,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(63,21,23,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(64,21,24,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(65,20,7,0,30,17,0,47,0,'',NULL,'2026-07-17 02:48:34'),(66,20,8,0,30,17,0,47,0,'',NULL,'2026-07-17 02:48:34'),(67,20,9,0,30,6,0,36,0,'',NULL,'2026-07-17 02:48:34'),(68,20,10,0,30,13,0,43,0,'',NULL,'2026-07-17 02:48:34'),(69,20,11,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(70,17,7,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(71,17,8,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(72,17,9,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(73,17,10,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(74,17,11,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(75,16,7,0,30,17,0,47,0,'',NULL,'2026-07-17 02:48:34'),(76,16,8,0,30,17,0,47,0,'',NULL,'2026-07-17 02:48:34'),(77,16,9,0,30,17,0,47,0,'',NULL,'2026-07-17 02:48:34'),(78,16,10,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34'),(79,16,11,0,30,0,0,30,0,'',NULL,'2026-07-17 02:48:34');
/*!40000 ALTER TABLE `dedup_records` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `follow_up_records`
--

DROP TABLE IF EXISTS `follow_up_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `follow_up_records` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `person_id` bigint unsigned NOT NULL COMMENT '??????ԱID',
  `follow_date` date NOT NULL COMMENT '???????????',
  `content` text COLLATE utf8mb4_unicode_ci COMMENT '???????',
  `next_date` date DEFAULT NULL COMMENT '?´????????',
  `is_reminded` tinyint DEFAULT '0' COMMENT '?Ƿ??ѵ???????: 0=δ???? 1=?????',
  `recorder` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '??¼?',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_person_id` (`person_id`),
  KEY `idx_next_date` (`next_date`),
  KEY `idx_is_reminded` (`is_reminded`),
  CONSTRAINT `follow_up_records_ibfk_1` FOREIGN KEY (`person_id`) REFERENCES `person_profiles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='???ü?¼';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `follow_up_records`
--

LOCK TABLES `follow_up_records` WRITE;
/*!40000 ALTER TABLE `follow_up_records` DISABLE KEYS */;
/*!40000 ALTER TABLE `follow_up_records` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `person_profiles`
--

DROP TABLE IF EXISTS `person_profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `person_profiles` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '???',
  `id_card` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '????֤??(???ܴ洢)',
  `person_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '??Ա????: ?????ϰ?/?????ͷ?/????????/??????Ա?',
  `risk_level` tinyint DEFAULT '1' COMMENT '???յȼ?: 1=?? 2=?? 3=?',
  `departments` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???ܲ???(???ŷָ',
  `district` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?????????ֵ?',
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '??ϵ?绰',
  `remark` text COLLATE utf8mb4_unicode_ci COMMENT '??ע',
  `status` tinyint DEFAULT '1' COMMENT '״̬: 1=?ڹ? 2=?ѽ??',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_name` (`name`),
  KEY `idx_person_type` (`person_type`),
  KEY `idx_risk_level` (`risk_level`),
  KEY `idx_district` (`district`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='?ص???Ա????';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `person_profiles`
--

LOCK TABLES `person_profiles` WRITE;
/*!40000 ALTER TABLE `person_profiles` DISABLE KEYS */;
/*!40000 ALTER TABLE `person_profiles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `policy_library`
--

DROP TABLE IF EXISTS `policy_library`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `policy_library` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `policy_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '?????',
  `dept` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???????',
  `category` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???߷??',
  `target_group` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '???ö??',
  `conditions` text COLLATE utf8mb4_unicode_ci COMMENT '?????',
  `benefit_standard` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '????/??????׼',
  `procedure_desc` text COLLATE utf8mb4_unicode_ci COMMENT '?????',
  `keywords` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '?????ؼ',
  `is_active` tinyint DEFAULT '1' COMMENT '?Ƿ???Ч',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_dept` (`dept`),
  KEY `idx_category` (`category`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='???߷????';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `policy_library`
--

LOCK TABLES `policy_library` WRITE;
/*!40000 ALTER TABLE `policy_library` DISABLE KEYS */;
/*!40000 ALTER TABLE `policy_library` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_name` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `role` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'admin',
  `is_active` tinyint DEFAULT '1',
  `last_login` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'admin','$2b$12$F1Njhv6iGCPUpWLxQVfJOOxGqBK9zH8sRfjgGtt5AoSP2U1.D5hpu','管理员','admin',1,'2026-07-17 01:37:56','2026-07-17 01:35:46');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'fengqiao_zhidun'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-17  3:27:12
