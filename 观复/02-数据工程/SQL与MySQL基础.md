# SQL 与 MySQL 基础

> **定位**：本篇是 `02-数据工程` 的地基。[[数据仓库分层：从 ODS、DWD、DWS 到湖仓一体]] 讲的分层加工、[[API到MySQL数据采集实战]] 讲的入库，用的都是这里的语句。
> **核验状态**：部分实测——查询语义的十组例子曾在 SQLite 3.53.1 运行；`IFNULL`、`MODIFY`、`DIV`、存储过程等 MySQL 专有语法未在 MySQL 实例验证。详见 [[知识库质量审计]]。

## 背景：为什么数据工作绕不开 SQL

业务系统的数据几乎都躺在关系数据库里。要把它们取出来做分析、校验或加工，只有两条路：

1. 用程序（Python、Java）一行行读出来，在程序里算；
2. 用 SQL 告诉数据库"我要什么"，让它自己决定怎么算。

第二条路之所以胜出，是因为**数据库离数据最近**。数据存在磁盘上、有索引、有统计信息，数据库知道怎样读最省事。你把 100 万行拉到 Python 里再筛选，等于把一仓库货搬到院子里再挑；写一句 `WHERE`，是让仓库管理员在货架上直接挑。

这也是 ELT 能成立的原因：先把原始数据加载进数据库，再用 SQL 在库内加工（见 [[数据工程全景]]）。

## 问题：会写 `SELECT` 不等于会查数据

`SELECT * FROM t` 谁都会写。真正让人出错的是下面四件事：

| 容易出错的地方 | 典型后果 |
| --- | --- |
| 执行顺序与书写顺序不一致 | 在 `WHERE` 里引用刚起的别名，报错 |
| `NULL` 不是 0、也不是空字符串 | 该统计的没统计到，该匹配的匹配不上 |
| 连接会改变行数 | 汇总金额翻倍 |
| 类型与运算法则 | 在 SQLite 中，`1/3` 算出 `0`，比率全是 0 |

其中有些写法会报错，有些会正常返回错误结果。重点是理解语义并核对行数、类型与口径。

---

## 一、先建立模型：表、行、列与主键

关系数据库把所有东西放进二维表：

| 概念 | 含义 | 对应到业务 |
| --- | --- | --- |
| 表（table） | 一类对象的集合 | 订单、商品、员工 |
| 行（row / record） | 一个具体的对象 | 一笔订单 |
| 列（column / field） | 对象的一个属性 | 订单金额、下单时间 |
| 主键（primary key） | 能唯一标识一行的列或列组合 | 订单号 |
| 外键（foreign key） | 指向另一张表主键的列 | 订单里的商品 ID |

在动手写任何查询之前，先回答一个问题：**这一行代表什么**。这就是 [[数据认知框架]] 讲的粒度。粒度没想清楚，SQL 写得再对，结果也是错的——因为它算的不是你以为的那个东西。

---

## 二、SQL 的五大家族：一张地图

SQL 语句按用途分成五类，名字看着唬人，其实是按"管什么"分的：

| 家族 | 全称 | 管什么 | 代表语句 |
| --- | --- | --- | --- |
| DDL | 数据定义语言 | 管**结构**：库、表、列、索引 | `CREATE`、`ALTER`、`DROP` |
| DML | 数据操纵语言 | 管**行**：增、删、改 | `INSERT`、`UPDATE`、`DELETE` |
| DQL | 数据查询语言 | 管**读** | `SELECT` |
| DCL | 数据控制语言 | 管**权限** | `GRANT`、`REVOKE` |
| TCL | 事务控制语言 | 管**提交与回滚** | `COMMIT`、`ROLLBACK` |

查询是数据工作的常用入口；DDL 决定表的结构，事务控制决定一组改动如何提交或撤销。

---

## 三、查询：书写顺序与执行顺序

这是理解 SQL 的分水岭。

**书写顺序**（你打字时的顺序）：

~~~text
SELECT → DISTINCT → FROM → JOIN → ON → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT
~~~

**逻辑处理顺序**（理解语义的模型；实际物理执行计划可能重排）：

~~~text
1. FROM       先确定从哪张表取数据
2. JOIN       一张表不够就再关联别的表；不写关联条件会产生笛卡儿积
3. ON         判断连接条件；外连接还会补回保留侧的未匹配行
4. WHERE      在整合好的大表上做行级筛选
5. GROUP BY   把指定列取值相同的行并成一组
6. HAVING     分组之后再筛选（与 WHERE 的差别就是中间多了 GROUP BY）
7. SELECT     行处理结束，转到列处理：算表达式、起别名
8. DISTINCT   对整行去重
9. ORDER BY   排序
10. LIMIT     决定返回哪些行
~~~

### 3.1 为什么这个顺序重要

顺序决定了"某一步能不能看到上一步的产物"。三个可以直接观察到的后果：

**后果一：`WHERE` 里用不了聚合函数。** 因为 `WHERE` 在第 4 步执行，`GROUP BY` 在第 5 步，分组还没发生。

~~~sql
-- 报错：misuse of aggregate: COUNT()
SELECT grp FROM t WHERE COUNT(*) > 1 GROUP BY grp;
~~~

**后果二：窗口函数不能写在 `WHERE` 里。** 窗口函数在第 7 步（`SELECT`）才算，`WHERE` 比它早三步。

~~~sql
-- 报错：misuse of window function ROW_NUMBER()
SELECT ename FROM emp WHERE ROW_NUMBER() OVER (ORDER BY sal) = 1;

-- 正确做法：先用子查询把窗口列算出来，外层再筛
SELECT ename, rn
FROM (SELECT ename, ROW_NUMBER() OVER (ORDER BY sal DESC) AS rn FROM emp)
WHERE rn = 1;
~~~

**后果三：`ORDER BY` 可以用 `SELECT` 里新起的别名。** 因为 `ORDER BY`（第 9 步）在 `SELECT`（第 7 步）之后。

~~~sql
SELECT sal AS s FROM emp WHERE sal > 2500 ORDER BY s DESC;   -- 可用
~~~

### 3.2 一个必须知道的分歧：别名能不能在 `WHERE` 里用

这里各家数据库行为**不一致**，容易踩坑：

| 位置 | 标准 SQL / MySQL | SQLite |
| --- | --- | --- |
| `WHERE` 用 `SELECT` 的别名 | **不允许**，报 `Unknown column` | 允许（SQLite 的扩展） |
| `ORDER BY` 用别名 | 允许 | 允许 |
| `GROUP BY` / `HAVING` 用别名 | 允许 | 允许 |

实测记录：在 SQLite 3.53 上，`SELECT id, v*2 AS double_v FROM t WHERE double_v > 300` 能正常返回结果。**换到 MySQL 会报错**——所以不要把这条当通用规则记，记住的是背后的原因：`WHERE` 执行时别名还不存在，允许它只是个别数据库的宽容。

---

## 四、`NULL`：SQL 里最反直觉的东西

`NULL` 不是 0，不是空字符串，它的语义是"**未知**"。这个定义决定了它的全部怪异行为。

### 4.1 三值逻辑

既然 `NULL` 是"未知"，那么"未知等于未知吗"——**不知道**。所以结果是 `NULL`，而不是 `true`：

~~~sql
SELECT (NULL = NULL) AS eq, (NULL <> NULL) AS neq;
-- 结果：(NULL, NULL)
~~~

这意味着：**任何涉及 `NULL` 的比较都不会命中**。`WHERE comm = NULL` 永远查不出任何行，必须写 `WHERE comm IS NULL`。

### 4.2 `COUNT(*)` 与 `COUNT(列)` 不是一回事

~~~sql
SELECT COUNT(*) AS 全部行, COUNT(comm) AS 非空行 FROM emp;
-- 结果：(9, 2)
~~~

- `COUNT(*)`：数行数，`NULL` 也算一行；
- `COUNT(列)`：只数**该列不为 `NULL`** 的行。

这一条直接决定了"有效订单数"之类的指标怎么写。用错会使指标偏离定义，可能高估或低估。

### 4.3 `NULL` 在聚合里：被跳过，但整组全空时返回 `NULL`

~~~sql
SELECT SUM(comm) AS s, AVG(comm) AS a, COUNT(comm) AS c FROM emp;
-- 结果：(800, 400.0, 2)
~~~

`SUM` / `AVG` / `MAX` / `MIN` 都会忽略 `NULL`。所以 `AVG(comm)` 的分母是 2 而不是 9——**平均值自动变成了"有奖金者的平均奖金"**，这往往不是业务想要的口径。

如果整组全是 `NULL`，`SUM` 返回 `NULL` 而不是 0：

~~~sql
SELECT SUM(v) FROM t WHERE grp = 'C';   -- 结果：NULL（不是 0）
~~~

所以做报表时通常要包一层：`COALESCE(SUM(v), 0)`。

### 4.4 `NULL` 在排序里：先确认数据库方言

~~~sql
SELECT id, v FROM t ORDER BY v;       -- SQLite / MySQL：NULL 排最前
SELECT id, v FROM t ORDER BY v DESC;  -- SQLite / MySQL：NULL 排最后
~~~

### 4.5 处理 `NULL` 的写法

| 需求 | MySQL | Oracle |
| --- | --- | --- |
| 空值替换为默认值 | `IFNULL(x, 0)` | `NVL(x, 0)` |
| 多个候选取第一个非空 | `COALESCE(a, b, c)` | `COALESCE(a, b, c)` |
| 按是否为空返回不同值 | `IF(x IS NULL, a, b)` / `CASE` | `NVL2(x, a, b)` |
| 判空 | `IS NULL` / `IS NOT NULL` | 同左 |

`COALESCE` 是标准 SQL，两边都能用，优先记它。

### 4.6 一个真实陷阱：`NOT IN` 遇到 `NULL` 会返回空

这是最隐蔽的一种错误。子查询结果里只要混进一个 `NULL`，`NOT IN` 就永远返回空结果集：

~~~sql
-- 意图：找出不属于"有奖金部门"的员工
SELECT ename FROM emp
WHERE deptno NOT IN (SELECT deptno FROM emp WHERE comm IS NULL);
-- 结果：空
~~~

原因：`deptno NOT IN (20, 30, NULL)` 展开后包含 `deptno <> NULL`，而它的结果永远是 `NULL`（未知），整条条件因此无法成立。

**规避**：改用 `NOT EXISTS`，或在子查询里加 `WHERE deptno IS NOT NULL`。

---

## 五、数据类型与隐式转换

### 5.1 常见类型

| 类型 | 用途 | 备注 |
| --- | --- | --- |
| `INT` | 整数 | 主键、数量 |
| `DECIMAL(p, s)` / `NUMERIC(p, s)` | 定点小数 | **金额必须用这个**，不用 `FLOAT` |
| `VARCHAR(n)` | 变长字符串 | Oracle 里叫 `VARCHAR2` |
| `DATE` / `DATETIME` / `TIMESTAMP` | 日期时间 | 区别在精度与时区语义 |
| `TEXT` | 长文本 | 原始响应、日志 |

金额不要用浮点：`FLOAT` 存的是近似值，累加会出现 `0.1 + 0.2 != 0.3` 这类误差，对账时找不到原因。

### 5.2 整数除法：报表里最容易出错的一处

两个整数相除，不同数据库给出的结果不同：

~~~sql
SELECT 5/2 AS 整除, 5.0/2 AS 浮点, CAST(5 AS REAL)/2 AS 显式转换;
-- SQLite 结果：(2, 2.5, 2.5)
~~~

~~~sql
SELECT 1/3 AS 错, 100.0*1/3 AS 对, ROUND(100.0*1/3, 2) AS 保留两位;
-- SQLite 结果：(0, 33.333333333333336, 33.33)
~~~

**在 SQLite 中，整数 `1/3` 得到 `0`**；MySQL 的 `/` 返回小数。跨库编写比率时要显式确定数值类型。

| 数据库 | `5/2` 的结果 | 说明 |
| --- | --- | --- |
| SQLite | `2` | 整数相除取整（已实测） |
| MySQL | `2.5000` | `/` 总是返回小数，整除要用 `DIV`（**未实测，依官方文档**） |

所以写比率时**显式保证有一个操作数是小数**：`100.0 * a / b`，或 `CAST(a AS DECIMAL(10,4)) / b`。这条规则在两个数据库上都安全。

### 5.3 比较规则

| 类型 | 比较方式 |
| --- | --- |
| 数字 | 按数值大小 |
| 字符串 | 逐位比较字符编码（所以 `'10' < '9'`） |
| 日期 | 按时间先后，越早越小 |

字符串比大小的反直觉之处（已实测）：

~~~sql
SELECT '10' > '9' AS 字符串比较, 10 > 9 AS 数字比较;
-- 结果：(0, 1)
~~~

**推论**：以字符串存的数字（`'007'`、`'10'`）排序和比较都会出错。这类列要么存成数字，要么比较时显式转换。

---

## 六、连接：为什么行数会变多

### 6.1 先看笛卡儿积

不写关联条件时，数据库会把两张表**逐行两两组合**：

~~~sql
SELECT COUNT(*) FROM emp, dept;   -- 9 行 × 4 行 = 36
~~~

9 名员工 × 4 个部门 = 36 行。这是"行数莫名其妙变多"的根本原因——汇总时金额会成倍放大。

### 6.2 四种连接

用 `emp`（9 行，其中 1 行的 `deptno = 99` 在 `dept` 里不存在）和 `dept`（4 行）实测：

| 连接 | 含义 | 实测行数 |
| --- | --- | --- |
| `INNER JOIN` | 只保留两表都匹配的行 | 8（丢掉了 `deptno = 99` 的员工） |
| `LEFT JOIN` | 保留左表全部行，右表无匹配则填 `NULL` | 9 |
| `RIGHT JOIN` | 保留右表全部行 | 9（多出 `dept 40` 一行，员工列为 `NULL`） |
| `FULL JOIN` | 两表全部保留 | **MySQL 不支持** |

`LEFT JOIN` 后未匹配的行长这样（右表列全为 `NULL`）：

~~~sql
SELECT e.ename, e.deptno, d.dname
FROM emp e LEFT JOIN dept d ON e.deptno = d.deptno
WHERE d.dname IS NULL;
-- 结果：('ORPHAN', 99, NULL)
~~~

### 6.3 MySQL 没有全外连接

`FULL OUTER JOIN` 是标准 SQL，但 MySQL 不实现。可以取全部左连接结果，再补上仅存在于右侧的行。这里 `empno` 是非空主键，故可用它识别未匹配行；`UNION ALL` 保留重复行语义：

~~~sql
SELECT e.empno, d.deptno
FROM emp e LEFT JOIN dept d ON e.deptno = d.deptno
UNION ALL
SELECT e.empno, d.deptno
FROM emp e RIGHT JOIN dept d ON e.deptno = d.deptno
WHERE e.empno IS NULL;
-- 构造数据：10 行（8 行匹配 + 1 行孤儿员工 + 1 行空部门）
~~~

### 6.4 `LEFT JOIN` 后的筛选条件决定是否保留未匹配行

~~~sql
SELECT COUNT(*) FROM emp e LEFT JOIN dept d ON e.deptno = d.deptno;
-- 9

SELECT COUNT(*) FROM emp e LEFT JOIN dept d ON e.deptno = d.deptno
WHERE d.dname IS NOT NULL;
-- 8
~~~

`d.dname IS NOT NULL` 排除了右侧未匹配行；这类对右表的排空条件会让结果失去外连接的保留效果。相反，`WHERE d.deptno IS NULL` 是查找未匹配左表行的常见写法。若要限制右表候选行而仍保留左表，把限制写在 `ON`；若要筛选最终结果，写在 `WHERE`。

### 6.5 连接基数：和 pandas 是同一件事

这里的坑与 [[Pandas索引与数据对齐]] 讲的**连接基数**完全同源：一对多连接会让左表的行被复制。pandas 和 SQL 默认都可能安静地返回更多行。pandas `merge` 要显式传 `validate='one_to_one'` 或其他预期基数，才会检查连接键的唯一性；SQL 则需自行检查连接前后行数和键。

---

## 七、聚合与分组

### 7.1 `GROUP BY` 在做什么

`GROUP BY grp` 的含义是：把 `grp` 取值相同的行并成一组，然后对每组算一个结果。执行顺序上它排在第 5 步，在 `WHERE` 之后、`HAVING` 之前。

~~~sql
SELECT deptno, COUNT(*) AS 人数, SUM(sal) AS 总额
FROM emp GROUP BY deptno ORDER BY deptno;
~~~

### 7.2 `WHERE` 与 `HAVING` 的分工

一句话：**`WHERE` 在分组前筛行，`HAVING` 在分组后筛组**。

~~~sql
SELECT deptno, COUNT(*) AS 人数
FROM emp
WHERE sal > 1000          -- 先丢掉工资 ≤ 1000 的行
GROUP BY deptno
HAVING COUNT(*) >= 2;     -- 再把人数不足 2 的组丢掉
~~~

效率上应尽量把条件放进 `WHERE`：越早减少行数，后面每一步的代价越小。

### 7.3 选非分组列的坑

~~~sql
SELECT grp, id, MAX(v) FROM t GROUP BY grp;
-- 实测：('A', 3, 200)  ('B', 4, 300)
~~~

`id` 没有分组也没有聚合。SQLite 对**恰有一个内置 `MIN()` 或 `MAX()`** 的查询有特殊规则：裸列取自达到极值的某一行；若并列，具体取哪一行不确定。因此此例的 `id` 与 `MAX(v)` 来自同一行，但不能据此推断所有数据库或所有聚合都如此。

- MySQL 开启 `ONLY_FULL_GROUP_BY` 时，若裸列不能由分组列唯一确定，就会报错；关闭后可能返回不确定值。
- SQLite 允许裸列；本例适用上述 `MAX()` 特例。
- Oracle 通常要求所选列被分组或聚合。

可移植的写法是让所选列参与分组或聚合；需要“最大值所在整行”时，用 `ROW_NUMBER()` 等方法显式定义并列时的选择。MySQL 对由分组列函数依赖确定的列有额外许可。

---

## 八、窗口函数：不折叠行的聚合

聚合把多行压成一行；窗口函数在每一行旁边**再加一列**结果，行数不变。

### 8.1 `OVER` 与 `PARTITION BY`

~~~sql
SELECT ename, sal,
       SUM(sal) OVER ()                    AS 全表合计,
       SUM(sal) OVER (PARTITION BY deptno) AS 部门合计
FROM emp;
~~~

`OVER ()` 表示"整个结果集是一个窗口"；`PARTITION BY` 相当于窗口内部的 `GROUP BY`，但**不合并行**。

典型用途：算"每行占总额的比例"——这正是 `GROUP BY` 做不到的，因为它会把明细行消灭掉。

### 8.2 三种排名的差别

只有当**出现并列**时差别才显现。实测数据（A 组按 `v` 排序：100、100、200）：

| 行 | `v` | `ROW_NUMBER()` | `RANK()` | `DENSE_RANK()` |
| --- | --- | --- | --- | --- |
| 第 1 行 | 100 | 1 | 1 | 1 |
| 第 2 行 | 100 | 2 | 1 | 1 |
| 第 3 行 | 200 | 3 | **3** | **2** |

- `ROW_NUMBER()`：永远连续不重复，**适合取 Top N 的"第几行"**；
- `RANK()`：并列同名次，**跳号**，适合体育式排名；
- `DENSE_RANK()`：并列同名次，**不跳号**，适合"有几种档位"。

选错会导致"取前 3 名"取到 4 行或 2 行。

### 8.3 `LAG()` 与 `LEAD()`

取当前行之前/之后某一行的值，用于算环比、增量、留存：

~~~sql
SELECT empno, sal,
       LAG(sal)  OVER (ORDER BY empno) AS 上一行,
       LEAD(sal) OVER (ORDER BY empno) AS 下一行
FROM emp ORDER BY empno;
~~~

首行的 `LAG`、末行的 `LEAD` 返回 `NULL`。

### 8.4 `ORDER BY` 的累加陷阱

窗口里的 `ORDER BY` **不只是排序，还决定累加范围**。默认框架是"从起点到当前行"：

~~~sql
SELECT empno, sal, SUM(sal) OVER (ORDER BY empno) AS 累加 FROM emp ORDER BY empno;
-- 800 → 2400 → 3650 → 6625 → 9475 → 11925 → 16925 → 17875 → 18875
~~~

**要总数而不是累加，必须去掉 `ORDER BY` 或显式指定框架**：

~~~sql
SUM(sal) OVER (ORDER BY empno
               ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
~~~

这是"我要合计，结果出来一串递增数字"的常见原因。

### 8.5 窗口函数不能写在 `WHERE`

见 3.1 的后果二。过滤窗口结果必须先包成子查询再在外层筛。

---

## 九、改数据：`INSERT` / `UPDATE` / `DELETE` 与事务

| 操作 | 写法 |
| --- | --- |
| 全字段插入 | `INSERT INTO 表 VALUES (值1, 值2, ...)` |
| 指定字段插入 | `INSERT INTO 表 (列1, 列2) VALUES (值1, 值2)` |
| 用查询结果插入 | `INSERT INTO 表 (列1, 列2) SELECT 列1, 列2 FROM 源表` |
| 更新 | `UPDATE 表 SET 列 = 值 WHERE 条件` |
| 删除 | `DELETE FROM 表 WHERE 条件` |

**三条必须养成的习惯**：

1. **先 `SELECT` 后 `UPDATE`**：把 `WHERE` 条件先写成 `SELECT` 跑一遍，确认命中的行数与你预期一致，再改成 `UPDATE`。
2. **`UPDATE` / `DELETE` 不写 `WHERE` 会作用于全表**。没有语法错误，没有二次确认。
3. **改前确认事务状态**：MySQL 新连接默认开启 `autocommit`，单条成功的 DML 会立即提交，之后的 `ROLLBACK` 无法撤销。需要成组检查和回滚时，先 `START TRANSACTION`，核对后再 `COMMIT` 或 `ROLLBACK`；同时确认客户端/连接的实际设置。

在数据管道里还要多一层考虑：**重复运行会不会产生重复数据**。这就是 [[数据工程全景]] 里说的幂等性，具体做法见 [[API到MySQL数据采集实战]] 的 ODS 快照部分。

---

## 十、表结构：DDL 与约束

### 10.1 建表

~~~sql
CREATE TABLE emp (
    empno  INT PRIMARY KEY,
    ename  VARCHAR(20) NOT NULL,
    deptno INT,
    sal    DECIMAL(10,2)
);

-- 按查询结果建表（复制查询列和数据，不会完整复制原表的键、索引与约束）
CREATE TABLE emp_bak AS SELECT * FROM emp;

-- 只要结构不要数据
CREATE TABLE emp_empty AS SELECT * FROM emp WHERE 1 = 0;
~~~

> 来源笔记里用的是 `WHERE 1 != 1`，同理；用 `1 = 0` 更直观。

### 10.2 修改表结构

| 目标 | 语句 |
| --- | --- |
| 加列 | `ALTER TABLE 表 ADD COLUMN 列 类型` |
| 删列 | `ALTER TABLE 表 DROP COLUMN 列` |
| 改列定义 | `ALTER TABLE 表 MODIFY COLUMN 列 新类型`（MySQL） |
| 改列名 | `ALTER TABLE 表 RENAME COLUMN 旧名 TO 新名` |
| 改表名 | `ALTER TABLE 旧表 RENAME TO 新表` 或 `RENAME TABLE 旧表 TO 新表` |

MySQL 的 `MODIFY` **不能改名**，改名要用 `CHANGE`（`ALTER TABLE t CHANGE 旧列 新列 类型`）。

### 10.3 索引

索引为查找提供路径，但优化器仍可能选择全表扫描。在 InnoDB 中，`PRIMARY KEY` 对应名为 `PRIMARY` 的聚集索引；`UNIQUE` 键通常是独立的二级索引。无主键时，InnoDB 才按规则选用合适的唯一索引或生成隐藏聚集索引。

~~~sql
CREATE [UNIQUE] INDEX 索引名 ON 表名 (列名);
~~~

代价要清楚：索引加速读，拖慢写（每次写入都要维护索引），并占空间。所以不是越多越好，而是**按实际查询的 `WHERE` / `JOIN` 条件建**。

### 10.4 约束

| 约束 | 作用 |
| --- | --- |
| `PRIMARY KEY` | 唯一且非空，一行一个身份 |
| `UNIQUE` | 取值不重复 |
| `NOT NULL` | 不允许空 |
| `FOREIGN KEY` | 引用另一张表的主键，保证引用完整 |
| `CHECK` | 取值必须满足条件 |

约束是"把数据质量规则写进结构"——比事后写脚本检查更可靠，因为违规数据根本写不进去。这与 [[数据治理建设笔记]] 说的"把规则做成检查"是同一件事的两种粒度。

---

## 十一、视图、触发器与存储过程

### 11.1 视图

视图是**保存下来的查询**，用起来像表，本身不存数据。

~~~sql
CREATE VIEW order_view AS
SELECT id, customer_id, product, quantity, total_price
FROM orders
WHERE customer_id = 1
WITH CHECK OPTION;
~~~

`WITH CHECK OPTION` 的效果：通过视图插入或更新时，数据必须仍然满足视图定义的条件。上面这个视图只放行 `customer_id = 1` 的记录，这约束的是**经此视图写入的数据**；读取权限还要通过权限配置控制，不能仅凭 `WITH CHECK OPTION` 实现行级授权。

| 操作 | 语句 |
| --- | --- |
| 查看视图定义 | `SHOW CREATE VIEW 视图名` |
| 列出所有视图 | `SHOW FULL TABLES IN 库名 WHERE TABLE_TYPE LIKE 'VIEW';` |
| 删除 | `DROP VIEW 视图名` |

### 11.2 触发器

触发器是"某张表发生增删改时自动执行的代码"：

~~~sql
DELIMITER //
CREATE TRIGGER 触发器名
    BEFORE INSERT ON 表名
    FOR EACH ROW
BEGIN
    -- 执行语句
END;
//
DELIMITER ;
~~~

### 11.3 存储过程

存储过程是把一组 SQL 存进数据库，用 `CALL` 调用。

~~~sql
DELIMITER $$
CREATE PROCEDURE get_client(IN state CHAR(2))
BEGIN
    SELECT * FROM clients AS c WHERE c.state = state;
END$$
DELIMITER ;
~~~

`DELIMITER` 的作用是把语句结束符临时从 `;` 改成 `$$`——否则过程体内部的 `;` 会提前结束整条 `CREATE PROCEDURE`。这是初学者最常见的创建失败原因。

**参数与变量**：

| 概念 | 写法 | 说明 |
| --- | --- | --- |
| 输入参数 | `IN 名 类型` | 调用时传入 |
| 输出参数 | `OUT 名 类型` | 用 `SELECT ... INTO 变量` 写回 |
| 局部变量 | `DECLARE 名 类型 [DEFAULT 值]` | 过程内临时使用 |

参数校验与报错：

~~~sql
IF payment_amount <= 0 THEN
    SIGNAL SQLSTATE '22003' SET MESSAGE_TEXT = 'Invalid payment amount';
END IF;
~~~

### 11.4 在数据工程里：优先考虑不用

这三样都是**把业务逻辑藏进数据库**。在数据管道中要谨慎：

- 逻辑写在库里，版本控制、代码评审、单元测试都很难覆盖；
- 换数据库（MySQL → 数仓）时基本要重写；
- 排查问题时，读代码的人看不到它——它在你没打开的另一个地方自动执行。

常见做法是把转换逻辑放在 SQL 文件、dbt 模型或 Python 里（见 [[数据仓库分层：从 ODS、DWD、DWS 到湖仓一体]]），数据库只负责存储与查询。

---

## 十二、SQL 在数据链路里的位置

~~~mermaid
flowchart LR
    A[业务库 / API] --> B[ODS 原始层]
    B --> C[DWD 明细层<br/>清洗、去重、统一字段]
    C --> D[DIM 维度表<br/>产品、用户、日期]
    C --> E[DWS 汇总层<br/>口径收敛]
    D --> E
    E --> F[ADS / 报表 / 模型]
    style A fill:#E6F1FB,stroke:#185FA5,stroke-width:0.5px
    style B fill:#E1F5EE,stroke:#0F6E56,stroke-width:0.5px
    style C fill:#E1F5EE,stroke:#0F6E56,stroke-width:0.5px
    style D fill:#FAEEDA,stroke:#854F0B,stroke-width:0.5px
    style E fill:#FAEEDA,stroke:#854F0B,stroke-width:0.5px
    style F fill:#EEEDFE,stroke:#534AB7,stroke-width:0.5px
~~~

图中**每一层的加工语言都是本篇的语句**：ODS 靠 `INSERT ... SELECT` 落地，DWD 靠 `JOIN` 补维度、`ROW_NUMBER` 去重，DWS 靠 `GROUP BY` 收敛口径。分层是"把 SQL 放在哪一步写"的组织方式，不是另一门技术。

---

## 常见误区

1. **`WHERE` 里用 `SELECT` 起的别名**——MySQL 报错，SQLite 放过。别依赖它。
2. **`WHERE comm = NULL`**——永远返回空，必须用 `IS NULL`。
3. **`COUNT(列)` 当 `COUNT(*)` 用**——有 `NULL` 时低估行数。
4. **`NOT IN` 的子查询里带 `NULL`**——结果静默为空，改用 `NOT EXISTS`。
5. **两个整数相除算比率**——SQLite 的 `1/3` 得到 `0`，MySQL 的 `/` 行为不同；跨库时显式选用小数类型。
6. **`LEFT JOIN` 后过滤右表**——排空条件会去掉未匹配行；要保留左表且限制右表候选行，把条件放进 `ON`。
7. **`GROUP BY` 后选非分组列**——MySQL 受 `ONLY_FULL_GROUP_BY` 和函数依赖影响；SQLite 有 `MIN`/`MAX` 特例。不要依赖隐含选行。
8. **窗口 `ORDER BY` 当成纯排序**——加出累加值，要总数须显式指定框架。
9. **金额用 `FLOAT`**——浮点误差，对账时找不到原因，用 `DECIMAL`。
10. **`UPDATE` / `DELETE` 忘写 `WHERE`**——无语法错误、无二次确认，直接作用于全表。
11. **把 `FULL JOIN` 当成通用写法**——MySQL 不支持；等价改写须考虑未匹配行和重复行，见 6.3 节。
12. **跨库照抄方言函数或类型**——`NVL`、`TO_CHAR`、`VARCHAR2` 等需逐项核对 MySQL 对应写法；`SYSDATE()` 在 MySQL 也存在，但语义仍须核对。

---

## 现阶段认知

学 SQL 时，我把语句分成三层来记，效果比背语法好：

1. **模型层**：表、行、列、主键、粒度。这层决定"我问的问题对不对"。
2. **语义层**：逻辑查询顺序。这层解释为什么某些位置不能使用聚合或窗口函数，也帮助定位一部分报错。
3. **语句层**：具体语法。这层最容易被搜索替代，价值最低。

真正拉开差距的是第 2 层。它也是唯一一层**能解释为什么**的：`WHERE` 不能用聚合、窗口函数不能用 `WHERE`、`ORDER BY` 能用别名，看起来是三件不相干的事，实际是同一个顺序的不同侧面。

另一个认知：**SQL 不会替你发现逻辑错误**。它只在语法和约束层面把关。行数变多了、`NULL` 被跳过了、SQLite 整数除法把比率清零了——这三种错全都安静地返回结果。所以每次查询完，都要多问一句"这个行数合理吗"。

---

## 来源与整理说明


- **来源本身的问题**：原提纲通篇混用 Oracle 语法（`NVL`、`NVL2`、`TO_CHAR`、`TO_DATE`、`SYSDATE`、`ADD_MONTHS`、`LAST_DAY`、`VARCHAR2`、`NUMBER`、`SCOTT`/`EMP` 教学表），实际是一份 **Oracle SQL 学习记录**，却被命名为 MySQL。本篇按 MySQL 为准重写，Oracle 写法只在本篇的对照表里保留。
- **实测范围（重要）**：本篇的查询语义用 **SQLite 3.53.1**（Python 3.13 内置）实际运行验证，覆盖执行顺序的三个可观察后果、`NULL` 三值逻辑与聚合、四种连接的行数、三种排名函数的并列差异、窗口累加框架、`NOT IN` 的空结果陷阱、整数除法、字符串比较、`LIKE ... ESCAPE`。
- **未实测范围**：**本机没有 MySQL 实例**，所有 MySQL 专有语法（`IFNULL`、`MODIFY`、`DIV`、`ONLY_FULL_GROUP_BY`、`SIGNAL`、`DELIMITER`、存储过程、触发器）**未在真实 MySQL 上运行**，依官方文档整理。
- **已知的跨库差异**（不要当通用规则记）：
  | 行为 | SQLite | MySQL |
  | --- | --- | --- |
  | `WHERE` 用 `SELECT` 别名 | 允许（扩展） | 报错 |
  | 整数相除 `5/2` | `2` | `2.5000` |
  | `GROUP BY` 选非分组列 | 允许；单个内置 `MIN`/`MAX` 有特殊选行规则 | `ONLY_FULL_GROUP_BY` 开启且无函数依赖时拒绝 |
- **核验来源**：[MySQL 外连接优化](https://dev.mysql.com/doc/refman/8.4/en/outer-join-simplification.html)、[MySQL 分组规则](https://dev.mysql.com/doc/refman/8.4/en/group-by-handling.html)、[MySQL 事务提交](https://dev.mysql.com/doc/refman/en/innodb-autocommit-commit-rollback.html)、[InnoDB 索引类型](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html)、[SQLite 裸列规则](https://www.sqlite.org/lang_select.html)、[pandas merge 参数](https://pandas.pydata.org/docs/reference/api/pandas.merge.html)。
- **口径提醒**：本篇示例表沿用来源的经典 `EMP` / `DEPT` 结构（Oracle 教学用表），便于与原提纲对照；行数、部门编号均为构造数据。
