/* ============================================================================
   Azztec SaaS - client schema script
   Version          = schema 0002 - generated on 2026-11-07 by scripts/deploy_sql.py 1.0.1
   DO NOT HAND-EDIT   it is re-rendered from the migrations whenever they change
   Migrations       0001, 0002
   Needs            SQL Server 2016 or later

   WHEN    After every restore of the Workmate database, before the Azztec service starts.
   HOW     In SSMS, open a query window CONNECTED TO THE RESTORED WORKMATE DATABASE and run
           this whole file. It needs no SQLCMD mode. It contains no USE statement - it works
           on the database the window is connected to, and its first lines print which one.
   SAFE    Every step checks first and only creates what is missing, so running it twice,
           or on a database that already has part of it, changes nothing twice.
   CHECK   The last line printed must be AZZTEC SCHEMA OK.

   OPTIONAL   Set @AppLogin below to the login the Azztec service connects as. The
              script then re-creates that login's user in this database (a restore drops
              it) with db_datareader and db_datawriter only. Leave it empty to skip.
              When it is set, run the script as a sysadmin - the step reads the server's
              logins, which other accounts cannot see.

   WHAT IT ADDS - nothing else is touched
     14 tables, 15 columns on existing tables, 18 indexes, and dbo.alembic_version
       table dbo.Account_WorkCode
       table dbo.Action_Event
       table dbo.Action_Header
       table dbo.Auth_Event
       table dbo.Auth_Session
       table dbo.Diag_Log
       table dbo.Diag_NightShift
       table dbo.Diag_PM_Engine_Run
       table dbo.Email_Automation
       table dbo.External_Contractor
       table dbo.Home_View
       table dbo.Module_Settings
       table dbo.PO_Email_Log
       table dbo.WO_N_Plan
       column dbo.Location_Attachment.Creation_Date
       column dbo.Location_Attachment.User_id_Created_By
       column dbo.PO_Attachment.Creation_Date
       column dbo.PO_Attachment.User_id_Created_By
       column dbo.PO_Details.Invoice_Ref
       column dbo.Part_Attachment.Creation_Date
       column dbo.Part_Attachment.User_id_Created_By
       column dbo.Supplier.Email_2
       column dbo.Supplier.Email_3
       column dbo.WO_Attachment.Creation_Date
       column dbo.WO_Attachment.User_id_Created_By
       column dbo.WO_C_header.Source_Action_ID
       column dbo.WO_M_Attachment.Creation_Date
       column dbo.WO_M_Attachment.User_id_Created_By
       column dbo.WO_N_Header.Source_Action_ID
       index dbo.Account_WorkCode.UX_Account_WorkCode_Pair
       index dbo.Action_Event.IX_Action_Event_Action_Date
       index dbo.Action_Header.IX_Action_Header_Asset
       index dbo.Action_Header.IX_Action_Header_Owner
       index dbo.Action_Header.IX_Action_Header_Promoted
       index dbo.Action_Header.IX_Action_Header_RaisedBy
       index dbo.Action_Header.IX_Action_Header_Status_Entry
       index dbo.Auth_Event.IX_Auth_Event_IP
       index dbo.Auth_Event.IX_Auth_Event_Login
       index dbo.Auth_Session.IX_Auth_Session_User
       index dbo.Diag_Log.IX_Diag_Log_LoggedAt
       index dbo.Diag_Log.IX_Diag_Log_User_LoggedAt
       index dbo.Diag_NightShift.IX_Diag_NightShift_Run
       index dbo.Diag_PM_Engine_Run.IX_Diag_PM_Engine_Run_Started
       index dbo.External_Contractor.UX_External_Contractor_ShortId
       index dbo.Home_View.IX_Home_View_User
       index dbo.PO_Email_Log.IX_PO_Email_Log_PO_Id
       index dbo.PO_Email_Log.IX_PO_Email_Log_SentDate

   WHAT IT NEVER DOES
     writes or changes data in a Workmate table, changes an existing column, touches a
     view, a procedure or a trigger, or grants more than db_datareader and db_datawriter
   ============================================================================ */

SET NOCOUNT ON;
-- Session options as the migration ran them. sqlcmd starts with QUOTED_IDENTIFIER OFF, SSMS with ON.
SET NUMERIC_ROUNDABORT OFF;
SET ANSI_PADDING, ANSI_WARNINGS, CONCAT_NULL_YIELDS_NULL, ARITHABORT, QUOTED_IDENTIFIER, ANSI_NULLS ON;

-- Settings. Set the login the Azztec service uses, or leave empty to skip the app user step.
DECLARE @AppLogin sysname = '';

EXEC sp_set_session_context @key = N'azztec_app_login', @value = @AppLogin;
EXEC sp_set_session_context @key = N'azztec_app_user', @value = NULL;
PRINT CONCAT('azztec_schema 0002 - db=', DB_NAME(), ' server=', @@SERVERNAME, ' login=', SUSER_SNAME(),
             ' at=', CONVERT(varchar(19), GETDATE(), 120));
IF DB_NAME() IN (N'master', N'model', N'msdb', N'tempdb') OR OBJECT_ID(N'dbo.Users', N'U') IS NULL OR OBJECT_ID(N'dbo.WO_N_Header', N'U') IS NULL
BEGIN
    PRINT CONCAT('REFUSED - ', DB_NAME(), ' is not a Workmate database. Nothing was changed. ',
                 'Connect the query window to the restored Workmate database and run again.');
    RAISERROR('azztec_schema REFUSED - not a Workmate database', 16, 1);
    SET NOEXEC ON;
END
GO

-- Steps, in migration order. Each one checks first and creates only what is missing.

IF OBJECT_ID(N'dbo.Action_Header', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Action_Header (
    Action_ID bigint IDENTITY(1,1) NOT NULL,
    Short_Action_Id varchar(20) NOT NULL,
    Action_Title nvarchar(255) NOT NULL,
    Action_Description nvarchar(max) NULL,
    Asset_ID bigint NULL,
    Location_ID bigint NULL,
    Priority_ID bigint NULL,
    Status char(1) NOT NULL DEFAULT ''R'',
    Progress_ID int NOT NULL DEFAULT 1,
    Source varchar(50) NULL,
    Source_Detail nvarchar(255) NULL,
    Entry_Date datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Due_Date datetime NULL,
    User_Id_Created_By bigint NULL,
    User_Id_Raised_By bigint NULL,
    User_Id_Owner bigint NULL,
    User_Id_Ack_By bigint NULL,
    Acknowledgement_Date datetime NULL,
    User_Id_Approved_By bigint NULL,
    Approved_Date datetime NULL,
    User_ID_ClosedBy bigint NULL,
    Closed_Date datetime NULL,
    User_ID_CancelledBy bigint NULL,
    Cancelled_Date datetime NULL,
    Promoted_WO_ID bigint NULL,
    Promoted_Date datetime NULL,
    User_Id_Promoted_By bigint NULL,
    Notes nvarchar(max) NULL,
    User_Id_Last_Save bigint NULL,
    Last_Save_Date datetime NULL,
    PRIMARY KEY (Action_ID),
    CONSTRAINT UQ_Action_Header_ShortId UNIQUE (Short_Action_Id),
    CONSTRAINT CK_Action_Header_Status CHECK (Status=''G'' OR Status=''D'' OR Status=''C'' OR Status=''V'' OR Status=''A'' OR Status=''K'' OR Status=''P'' OR Status=''H'' OR Status=''R''),
    CONSTRAINT CK_Action_Progress CHECK (Progress_ID>=(1) AND Progress_ID<=(6))
)');
    IF OBJECT_ID(N'dbo.Action_Header', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Action_Header - read the error above';
    ELSE
        PRINT 'created table dbo.Action_Header';
END
ELSE PRINT 'present table dbo.Action_Header';
GO

IF OBJECT_ID(N'dbo.Action_Event', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Action_Event (
    Event_ID bigint IDENTITY(1,1) NOT NULL,
    Action_ID bigint NOT NULL,
    Event_Date datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Event_Type varchar(30) NOT NULL,
    Field_Name varchar(50) NULL,
    Old_Value nvarchar(255) NULL,
    New_Value nvarchar(255) NULL,
    User_Id bigint NULL,
    User_Id_Acting_For bigint NULL,
    Comment nvarchar(max) NULL,
    PRIMARY KEY (Event_ID),
    CONSTRAINT FK_Action_Event_Action FOREIGN KEY (Action_ID) REFERENCES dbo.Action_Header (Action_ID)
)');
    IF OBJECT_ID(N'dbo.Action_Event', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Action_Event - read the error above';
    ELSE
        PRINT 'created table dbo.Action_Event';
END
ELSE PRINT 'present table dbo.Action_Event';
GO

IF OBJECT_ID(N'dbo.Account_WorkCode', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Account_WorkCode (
    Sys_Account_WorkCode_Id numeric(18,0) IDENTITY(1,1) NOT NULL,
    Account_ID numeric(18,0) NOT NULL,
    WorkCode_ID numeric(18,0) NOT NULL,
    Default_WorkCode_ID char(1) NOT NULL DEFAULT ''F'',
    CONSTRAINT PK_Account_WorkCode PRIMARY KEY (Sys_Account_WorkCode_Id),
    CONSTRAINT FK_Account_WorkCode_Account FOREIGN KEY (Account_ID) REFERENCES dbo.Account (Account_ID),
    CONSTRAINT FK_Account_WorkCode_WorkCode FOREIGN KEY (WorkCode_ID) REFERENCES dbo.Work_Code (Work_Code_Id)
)');
    IF OBJECT_ID(N'dbo.Account_WorkCode', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Account_WorkCode - read the error above';
    ELSE
        PRINT 'created table dbo.Account_WorkCode';
END
ELSE PRINT 'present table dbo.Account_WorkCode';
GO

IF OBJECT_ID(N'dbo.External_Contractor', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.External_Contractor (
    Sys_External_Contractor_Id numeric(18,0) IDENTITY(1,1) NOT NULL,
    External_Contractor_ID numeric(18,0) NOT NULL,
    Short_External_Contractor_Id char(20) NOT NULL,
    Contractor_Name char(40) NOT NULL,
    Company_Name char(35) NULL,
    Contractor_Type char(1) NULL,
    Linked_Supplier_ID numeric(18,0) NULL,
    Phone varchar(20) NULL,
    Email varchar(100) NULL,
    Area varchar(20) NULL,
    Active char(1) NULL,
    Notes varchar(1000) NULL,
    Entry_Date datetime NULL,
    User_id_Created_By numeric(18,0) NULL,
    Server_Name varchar(50) NULL,
    CONSTRAINT PK_External_Contractor PRIMARY KEY (External_Contractor_ID),
    CONSTRAINT FK_External_Contractor_Supplier FOREIGN KEY (Linked_Supplier_ID) REFERENCES dbo.Supplier (Supplier_ID)
)');
    IF OBJECT_ID(N'dbo.External_Contractor', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.External_Contractor - read the error above';
    ELSE
        PRINT 'created table dbo.External_Contractor';
END
ELSE PRINT 'present table dbo.External_Contractor';
GO

IF OBJECT_ID(N'dbo.WO_N_Plan', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.WO_N_Plan (
    WO_ID numeric(18,0) NOT NULL,
    Pinned char(1) NOT NULL DEFAULT ''N'',
    Pinned_By numeric(18,0) NULL,
    Pinned_On datetime NULL,
    Prev_Start datetime NULL,
    Note varchar(255) NULL,
    Server_Name varchar(50) NULL,
    Entry_Date datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Last_Save_Date datetime NULL,
    CONSTRAINT PK_WO_N_Plan PRIMARY KEY (WO_ID)
)');
    IF OBJECT_ID(N'dbo.WO_N_Plan', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.WO_N_Plan - read the error above';
    ELSE
        PRINT 'created table dbo.WO_N_Plan';
END
ELSE PRINT 'present table dbo.WO_N_Plan';
GO

IF OBJECT_ID(N'dbo.Diag_Log', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Diag_Log (
    Diag_Id int IDENTITY(1,1) NOT NULL,
    Logged_At datetime2(3) NOT NULL,
    Session_Id varchar(64) NOT NULL,
    Wm_User_Id int NULL,
    Site_Code varchar(8) NULL,
    Source varchar(64) NOT NULL,
    Tier char(1) NOT NULL,
    Msg_Level varchar(8) NOT NULL,
    Message nvarchar(1000) NOT NULL,
    Detail nvarchar(max) NULL,
    CONSTRAINT PK_Diag_Log PRIMARY KEY (Diag_Id)
)');
    IF OBJECT_ID(N'dbo.Diag_Log', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Diag_Log - read the error above';
    ELSE
        PRINT 'created table dbo.Diag_Log';
END
ELSE PRINT 'present table dbo.Diag_Log';
GO

IF OBJECT_ID(N'dbo.Module_Settings', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Module_Settings (
    Module_Code varchar(30) NOT NULL,
    Is_Enabled char(1) NOT NULL DEFAULT ''N'',
    Notes varchar(255) NULL,
    Updated_Date datetime NULL,
    Updated_By varchar(30) NULL,
    Run_Token varchar(64) NULL,
    Run_Started datetime NULL,
    Run_Host varchar(80) NULL,
    CONSTRAINT PK_Module_Settings PRIMARY KEY (Module_Code)
)');
    IF OBJECT_ID(N'dbo.Module_Settings', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Module_Settings - read the error above';
    ELSE
        PRINT 'created table dbo.Module_Settings';
END
ELSE PRINT 'present table dbo.Module_Settings';
GO

IF OBJECT_ID(N'dbo.Diag_NightShift', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Diag_NightShift (
    Sys_Id int IDENTITY(1,1) NOT NULL,
    Run_Id int NOT NULL,
    Run_Started datetime NOT NULL,
    Run_Mode varchar(20) NULL,
    Pack varchar(60) NOT NULL,
    Test_Name varchar(120) NOT NULL,
    Ok int NULL,
    Detail varchar(2000) NULL,
    Duration_ms int NOT NULL DEFAULT 0,
    Cleanup_Ok int NULL,
    Lib_Version varchar(20) NULL,
    CONSTRAINT PK_Diag_NightShift PRIMARY KEY (Sys_Id)
)');
    IF OBJECT_ID(N'dbo.Diag_NightShift', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Diag_NightShift - read the error above';
    ELSE
        PRINT 'created table dbo.Diag_NightShift';
END
ELSE PRINT 'present table dbo.Diag_NightShift';
GO

IF OBJECT_ID(N'dbo.Diag_PM_Engine_Run', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Diag_PM_Engine_Run (
    Run_Id int IDENTITY(1,1) NOT NULL,
    Run_Started datetime NOT NULL,
    Run_Ended datetime NULL,
    Actor varchar(60) NULL,
    Host varchar(80) NULL,
    Masters int NULL,
    Released int NULL,
    Updated int NULL,
    Failed int NULL,
    Verdict varchar(24) NULL,
    Detail varchar(500) NULL,
    Lib_Version varchar(20) NULL,
    CONSTRAINT PK_Diag_PM_Engine_Run PRIMARY KEY (Run_Id)
)');
    IF OBJECT_ID(N'dbo.Diag_PM_Engine_Run', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Diag_PM_Engine_Run - read the error above';
    ELSE
        PRINT 'created table dbo.Diag_PM_Engine_Run';
END
ELSE PRINT 'present table dbo.Diag_PM_Engine_Run';
GO

IF OBJECT_ID(N'dbo.Home_View', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Home_View (
    Home_View_Id int IDENTITY(1,1) NOT NULL,
    User_ID numeric(18,0) NOT NULL,
    View_Title nvarchar(60) NOT NULL,
    Domain_Code char(1) NOT NULL DEFAULT ''W'',
    Criteria_Json nvarchar(max) NOT NULL,
    Sort_Order int NOT NULL DEFAULT 0,
    Active char(1) NOT NULL DEFAULT ''Y'',
    Crt_Date datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Upd_Date datetime NULL,
    CONSTRAINT PK_Home_View PRIMARY KEY (Home_View_Id),
    CONSTRAINT CK_Home_View_Domain CHECK (Domain_Code=''P'' OR Domain_Code=''W'')
)');
    IF OBJECT_ID(N'dbo.Home_View', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Home_View - read the error above';
    ELSE
        PRINT 'created table dbo.Home_View';
END
ELSE PRINT 'present table dbo.Home_View';
GO

IF OBJECT_ID(N'dbo.Email_Automation', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Email_Automation (
    Email_Automation_Id int IDENTITY(1,1) NOT NULL,
    Email_Key varchar(50) NOT NULL,
    Email_Title varchar(100) NOT NULL,
    Schedule_Text varchar(100) NULL,
    Is_Enabled char(1) NOT NULL DEFAULT ''Y'',
    Last_Sent datetime NULL,
    Last_Recipient_Count int NULL,
    Sort_Order int NOT NULL DEFAULT 0,
    PRIMARY KEY (Email_Automation_Id),
    CONSTRAINT UQ_Email_Automation_Key UNIQUE (Email_Key)
)');
    IF OBJECT_ID(N'dbo.Email_Automation', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Email_Automation - read the error above';
    ELSE
        PRINT 'created table dbo.Email_Automation';
END
ELSE PRINT 'present table dbo.Email_Automation';
GO

IF OBJECT_ID(N'dbo.PO_Email_Log', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.PO_Email_Log (
    Log_Id numeric(18,0) IDENTITY(1,1) NOT NULL,
    PO_Id numeric(18,0) NOT NULL,
    Sent_Date datetime NOT NULL,
    Sent_To_Email varchar(255) NOT NULL,
    Sent_To_Name varchar(100) NULL,
    Source char(1) NULL,
    Sent_By_User numeric(18,0) NULL,
    Batch_Title varchar(255) NULL,
    Is_Urgent char(1) NOT NULL DEFAULT ''N'',
    CONSTRAINT PK_PO_Email_Log PRIMARY KEY (Log_Id)
)');
    IF OBJECT_ID(N'dbo.PO_Email_Log', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.PO_Email_Log - read the error above';
    ELSE
        PRINT 'created table dbo.PO_Email_Log';
END
ELSE PRINT 'present table dbo.PO_Email_Log';
GO

IF COL_LENGTH(N'dbo.WO_N_Header', N'Source_Action_ID') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.WO_N_Header ADD Source_Action_ID bigint NULL');
    IF COL_LENGTH(N'dbo.WO_N_Header', N'Source_Action_ID') IS NULL
        PRINT 'NOT CREATED column dbo.WO_N_Header.Source_Action_ID - read the error above';
    ELSE
        PRINT 'created column dbo.WO_N_Header.Source_Action_ID';
END
ELSE PRINT 'present column dbo.WO_N_Header.Source_Action_ID';
GO

IF COL_LENGTH(N'dbo.WO_C_header', N'Source_Action_ID') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.WO_C_header ADD Source_Action_ID bigint NULL');
    IF COL_LENGTH(N'dbo.WO_C_header', N'Source_Action_ID') IS NULL
        PRINT 'NOT CREATED column dbo.WO_C_header.Source_Action_ID - read the error above';
    ELSE
        PRINT 'created column dbo.WO_C_header.Source_Action_ID';
END
ELSE PRINT 'present column dbo.WO_C_header.Source_Action_ID';
GO

IF COL_LENGTH(N'dbo.Supplier', N'Email_2') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.Supplier ADD Email_2 varchar(255) NULL');
    IF COL_LENGTH(N'dbo.Supplier', N'Email_2') IS NULL
        PRINT 'NOT CREATED column dbo.Supplier.Email_2 - read the error above';
    ELSE
        PRINT 'created column dbo.Supplier.Email_2';
END
ELSE PRINT 'present column dbo.Supplier.Email_2';
GO

IF COL_LENGTH(N'dbo.Supplier', N'Email_3') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.Supplier ADD Email_3 varchar(255) NULL');
    IF COL_LENGTH(N'dbo.Supplier', N'Email_3') IS NULL
        PRINT 'NOT CREATED column dbo.Supplier.Email_3 - read the error above';
    ELSE
        PRINT 'created column dbo.Supplier.Email_3';
END
ELSE PRINT 'present column dbo.Supplier.Email_3';
GO

IF COL_LENGTH(N'dbo.PO_Details', N'Invoice_Ref') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.PO_Details ADD Invoice_Ref varchar(30) NULL');
    IF COL_LENGTH(N'dbo.PO_Details', N'Invoice_Ref') IS NULL
        PRINT 'NOT CREATED column dbo.PO_Details.Invoice_Ref - read the error above';
    ELSE
        PRINT 'created column dbo.PO_Details.Invoice_Ref';
END
ELSE PRINT 'present column dbo.PO_Details.Invoice_Ref';
GO

IF COL_LENGTH(N'dbo.WO_Attachment', N'Creation_Date') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.WO_Attachment ADD Creation_Date datetime NULL');
    IF COL_LENGTH(N'dbo.WO_Attachment', N'Creation_Date') IS NULL
        PRINT 'NOT CREATED column dbo.WO_Attachment.Creation_Date - read the error above';
    ELSE
        PRINT 'created column dbo.WO_Attachment.Creation_Date';
END
ELSE PRINT 'present column dbo.WO_Attachment.Creation_Date';
GO

IF COL_LENGTH(N'dbo.WO_Attachment', N'User_id_Created_By') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.WO_Attachment ADD User_id_Created_By numeric(18,0) NULL');
    IF COL_LENGTH(N'dbo.WO_Attachment', N'User_id_Created_By') IS NULL
        PRINT 'NOT CREATED column dbo.WO_Attachment.User_id_Created_By - read the error above';
    ELSE
        PRINT 'created column dbo.WO_Attachment.User_id_Created_By';
END
ELSE PRINT 'present column dbo.WO_Attachment.User_id_Created_By';
GO

IF COL_LENGTH(N'dbo.WO_M_Attachment', N'Creation_Date') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.WO_M_Attachment ADD Creation_Date datetime NULL');
    IF COL_LENGTH(N'dbo.WO_M_Attachment', N'Creation_Date') IS NULL
        PRINT 'NOT CREATED column dbo.WO_M_Attachment.Creation_Date - read the error above';
    ELSE
        PRINT 'created column dbo.WO_M_Attachment.Creation_Date';
END
ELSE PRINT 'present column dbo.WO_M_Attachment.Creation_Date';
GO

IF COL_LENGTH(N'dbo.WO_M_Attachment', N'User_id_Created_By') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.WO_M_Attachment ADD User_id_Created_By numeric(18,0) NULL');
    IF COL_LENGTH(N'dbo.WO_M_Attachment', N'User_id_Created_By') IS NULL
        PRINT 'NOT CREATED column dbo.WO_M_Attachment.User_id_Created_By - read the error above';
    ELSE
        PRINT 'created column dbo.WO_M_Attachment.User_id_Created_By';
END
ELSE PRINT 'present column dbo.WO_M_Attachment.User_id_Created_By';
GO

IF COL_LENGTH(N'dbo.PO_Attachment', N'Creation_Date') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.PO_Attachment ADD Creation_Date datetime NULL');
    IF COL_LENGTH(N'dbo.PO_Attachment', N'Creation_Date') IS NULL
        PRINT 'NOT CREATED column dbo.PO_Attachment.Creation_Date - read the error above';
    ELSE
        PRINT 'created column dbo.PO_Attachment.Creation_Date';
END
ELSE PRINT 'present column dbo.PO_Attachment.Creation_Date';
GO

IF COL_LENGTH(N'dbo.PO_Attachment', N'User_id_Created_By') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.PO_Attachment ADD User_id_Created_By numeric(18,0) NULL');
    IF COL_LENGTH(N'dbo.PO_Attachment', N'User_id_Created_By') IS NULL
        PRINT 'NOT CREATED column dbo.PO_Attachment.User_id_Created_By - read the error above';
    ELSE
        PRINT 'created column dbo.PO_Attachment.User_id_Created_By';
END
ELSE PRINT 'present column dbo.PO_Attachment.User_id_Created_By';
GO

IF COL_LENGTH(N'dbo.Part_Attachment', N'Creation_Date') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.Part_Attachment ADD Creation_Date datetime NULL');
    IF COL_LENGTH(N'dbo.Part_Attachment', N'Creation_Date') IS NULL
        PRINT 'NOT CREATED column dbo.Part_Attachment.Creation_Date - read the error above';
    ELSE
        PRINT 'created column dbo.Part_Attachment.Creation_Date';
END
ELSE PRINT 'present column dbo.Part_Attachment.Creation_Date';
GO

IF COL_LENGTH(N'dbo.Part_Attachment', N'User_id_Created_By') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.Part_Attachment ADD User_id_Created_By numeric(18,0) NULL');
    IF COL_LENGTH(N'dbo.Part_Attachment', N'User_id_Created_By') IS NULL
        PRINT 'NOT CREATED column dbo.Part_Attachment.User_id_Created_By - read the error above';
    ELSE
        PRINT 'created column dbo.Part_Attachment.User_id_Created_By';
END
ELSE PRINT 'present column dbo.Part_Attachment.User_id_Created_By';
GO

IF COL_LENGTH(N'dbo.Location_Attachment', N'Creation_Date') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.Location_Attachment ADD Creation_Date datetime NULL');
    IF COL_LENGTH(N'dbo.Location_Attachment', N'Creation_Date') IS NULL
        PRINT 'NOT CREATED column dbo.Location_Attachment.Creation_Date - read the error above';
    ELSE
        PRINT 'created column dbo.Location_Attachment.Creation_Date';
END
ELSE PRINT 'present column dbo.Location_Attachment.Creation_Date';
GO

IF COL_LENGTH(N'dbo.Location_Attachment', N'User_id_Created_By') IS NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.Location_Attachment ADD User_id_Created_By numeric(18,0) NULL');
    IF COL_LENGTH(N'dbo.Location_Attachment', N'User_id_Created_By') IS NULL
        PRINT 'NOT CREATED column dbo.Location_Attachment.User_id_Created_By - read the error above';
    ELSE
        PRINT 'created column dbo.Location_Attachment.User_id_Created_By';
END
ELSE PRINT 'present column dbo.Location_Attachment.User_id_Created_By';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Status_Entry')
BEGIN
    EXEC(N'CREATE INDEX IX_Action_Header_Status_Entry ON dbo.Action_Header (Status, Entry_Date)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Status_Entry')
        PRINT 'NOT CREATED index dbo.Action_Header.IX_Action_Header_Status_Entry - read the error above';
    ELSE
        PRINT 'created index dbo.Action_Header.IX_Action_Header_Status_Entry';
END
ELSE PRINT 'present index dbo.Action_Header.IX_Action_Header_Status_Entry';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Asset')
BEGIN
    EXEC(N'CREATE INDEX IX_Action_Header_Asset ON dbo.Action_Header (Asset_ID)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Asset')
        PRINT 'NOT CREATED index dbo.Action_Header.IX_Action_Header_Asset - read the error above';
    ELSE
        PRINT 'created index dbo.Action_Header.IX_Action_Header_Asset';
END
ELSE PRINT 'present index dbo.Action_Header.IX_Action_Header_Asset';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Promoted')
BEGIN
    EXEC(N'CREATE INDEX IX_Action_Header_Promoted ON dbo.Action_Header (Promoted_WO_ID)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Promoted')
        PRINT 'NOT CREATED index dbo.Action_Header.IX_Action_Header_Promoted - read the error above';
    ELSE
        PRINT 'created index dbo.Action_Header.IX_Action_Header_Promoted';
END
ELSE PRINT 'present index dbo.Action_Header.IX_Action_Header_Promoted';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_RaisedBy')
BEGIN
    EXEC(N'CREATE INDEX IX_Action_Header_RaisedBy ON dbo.Action_Header (User_Id_Raised_By)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_RaisedBy')
        PRINT 'NOT CREATED index dbo.Action_Header.IX_Action_Header_RaisedBy - read the error above';
    ELSE
        PRINT 'created index dbo.Action_Header.IX_Action_Header_RaisedBy';
END
ELSE PRINT 'present index dbo.Action_Header.IX_Action_Header_RaisedBy';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Owner')
BEGIN
    EXEC(N'CREATE INDEX IX_Action_Header_Owner ON dbo.Action_Header (User_Id_Owner)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Owner')
        PRINT 'NOT CREATED index dbo.Action_Header.IX_Action_Header_Owner - read the error above';
    ELSE
        PRINT 'created index dbo.Action_Header.IX_Action_Header_Owner';
END
ELSE PRINT 'present index dbo.Action_Header.IX_Action_Header_Owner';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Event') AND name = N'IX_Action_Event_Action_Date')
BEGIN
    EXEC(N'CREATE INDEX IX_Action_Event_Action_Date ON dbo.Action_Event (Action_ID, Event_Date) INCLUDE (Event_Type, Field_Name, Old_Value, New_Value, User_Id, User_Id_Acting_For, Comment)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Event') AND name = N'IX_Action_Event_Action_Date')
        PRINT 'NOT CREATED index dbo.Action_Event.IX_Action_Event_Action_Date - read the error above';
    ELSE
        PRINT 'created index dbo.Action_Event.IX_Action_Event_Action_Date';
END
ELSE PRINT 'present index dbo.Action_Event.IX_Action_Event_Action_Date';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Account_WorkCode') AND name = N'UX_Account_WorkCode_Pair')
BEGIN
    EXEC(N'CREATE UNIQUE INDEX UX_Account_WorkCode_Pair ON dbo.Account_WorkCode (Account_ID, WorkCode_ID)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Account_WorkCode') AND name = N'UX_Account_WorkCode_Pair')
        PRINT 'NOT CREATED index dbo.Account_WorkCode.UX_Account_WorkCode_Pair - read the error above';
    ELSE
        PRINT 'created index dbo.Account_WorkCode.UX_Account_WorkCode_Pair';
END
ELSE PRINT 'present index dbo.Account_WorkCode.UX_Account_WorkCode_Pair';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.External_Contractor') AND name = N'UX_External_Contractor_ShortId')
BEGIN
    EXEC(N'CREATE UNIQUE INDEX UX_External_Contractor_ShortId ON dbo.External_Contractor (Short_External_Contractor_Id)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.External_Contractor') AND name = N'UX_External_Contractor_ShortId')
        PRINT 'NOT CREATED index dbo.External_Contractor.UX_External_Contractor_ShortId - read the error above';
    ELSE
        PRINT 'created index dbo.External_Contractor.UX_External_Contractor_ShortId';
END
ELSE PRINT 'present index dbo.External_Contractor.UX_External_Contractor_ShortId';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_Log') AND name = N'IX_Diag_Log_LoggedAt')
BEGIN
    EXEC(N'CREATE INDEX IX_Diag_Log_LoggedAt ON dbo.Diag_Log (Logged_At) INCLUDE (Wm_User_Id, Source, Tier)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_Log') AND name = N'IX_Diag_Log_LoggedAt')
        PRINT 'NOT CREATED index dbo.Diag_Log.IX_Diag_Log_LoggedAt - read the error above';
    ELSE
        PRINT 'created index dbo.Diag_Log.IX_Diag_Log_LoggedAt';
END
ELSE PRINT 'present index dbo.Diag_Log.IX_Diag_Log_LoggedAt';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_Log') AND name = N'IX_Diag_Log_User_LoggedAt')
BEGIN
    EXEC(N'CREATE INDEX IX_Diag_Log_User_LoggedAt ON dbo.Diag_Log (Wm_User_Id, Logged_At)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_Log') AND name = N'IX_Diag_Log_User_LoggedAt')
        PRINT 'NOT CREATED index dbo.Diag_Log.IX_Diag_Log_User_LoggedAt - read the error above';
    ELSE
        PRINT 'created index dbo.Diag_Log.IX_Diag_Log_User_LoggedAt';
END
ELSE PRINT 'present index dbo.Diag_Log.IX_Diag_Log_User_LoggedAt';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_NightShift') AND name = N'IX_Diag_NightShift_Run')
BEGIN
    EXEC(N'CREATE INDEX IX_Diag_NightShift_Run ON dbo.Diag_NightShift (Run_Id, Pack)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_NightShift') AND name = N'IX_Diag_NightShift_Run')
        PRINT 'NOT CREATED index dbo.Diag_NightShift.IX_Diag_NightShift_Run - read the error above';
    ELSE
        PRINT 'created index dbo.Diag_NightShift.IX_Diag_NightShift_Run';
END
ELSE PRINT 'present index dbo.Diag_NightShift.IX_Diag_NightShift_Run';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_PM_Engine_Run') AND name = N'IX_Diag_PM_Engine_Run_Started')
BEGIN
    EXEC(N'CREATE INDEX IX_Diag_PM_Engine_Run_Started ON dbo.Diag_PM_Engine_Run (Run_Started)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_PM_Engine_Run') AND name = N'IX_Diag_PM_Engine_Run_Started')
        PRINT 'NOT CREATED index dbo.Diag_PM_Engine_Run.IX_Diag_PM_Engine_Run_Started - read the error above';
    ELSE
        PRINT 'created index dbo.Diag_PM_Engine_Run.IX_Diag_PM_Engine_Run_Started';
END
ELSE PRINT 'present index dbo.Diag_PM_Engine_Run.IX_Diag_PM_Engine_Run_Started';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Home_View') AND name = N'IX_Home_View_User')
BEGIN
    EXEC(N'CREATE INDEX IX_Home_View_User ON dbo.Home_View (User_ID, Active, Sort_Order)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Home_View') AND name = N'IX_Home_View_User')
        PRINT 'NOT CREATED index dbo.Home_View.IX_Home_View_User - read the error above';
    ELSE
        PRINT 'created index dbo.Home_View.IX_Home_View_User';
END
ELSE PRINT 'present index dbo.Home_View.IX_Home_View_User';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.PO_Email_Log') AND name = N'IX_PO_Email_Log_PO_Id')
BEGIN
    EXEC(N'CREATE INDEX IX_PO_Email_Log_PO_Id ON dbo.PO_Email_Log (PO_Id, Sent_Date)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.PO_Email_Log') AND name = N'IX_PO_Email_Log_PO_Id')
        PRINT 'NOT CREATED index dbo.PO_Email_Log.IX_PO_Email_Log_PO_Id - read the error above';
    ELSE
        PRINT 'created index dbo.PO_Email_Log.IX_PO_Email_Log_PO_Id';
END
ELSE PRINT 'present index dbo.PO_Email_Log.IX_PO_Email_Log_PO_Id';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.PO_Email_Log') AND name = N'IX_PO_Email_Log_SentDate')
BEGIN
    EXEC(N'CREATE INDEX IX_PO_Email_Log_SentDate ON dbo.PO_Email_Log (Sent_Date)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.PO_Email_Log') AND name = N'IX_PO_Email_Log_SentDate')
        PRINT 'NOT CREATED index dbo.PO_Email_Log.IX_PO_Email_Log_SentDate - read the error above';
    ELSE
        PRINT 'created index dbo.PO_Email_Log.IX_PO_Email_Log_SentDate';
END
ELSE PRINT 'present index dbo.PO_Email_Log.IX_PO_Email_Log_SentDate';
GO

IF OBJECT_ID(N'dbo.Auth_Session', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Auth_Session (
    Session_Hash char(64) NOT NULL,
    User_ID numeric(18,0) NOT NULL,
    Created_Utc datetime2(3) NOT NULL,
    Last_Seen_Utc datetime2(3) NOT NULL,
    Expires_Utc datetime2(3) NOT NULL,
    Revoked_Utc datetime2(3) NULL,
    Client_IP varchar(45) NULL,
    User_Agent nvarchar(200) NULL,
    CONSTRAINT PK_Auth_Session PRIMARY KEY (Session_Hash)
)');
    IF OBJECT_ID(N'dbo.Auth_Session', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Auth_Session - read the error above';
    ELSE
        PRINT 'created table dbo.Auth_Session';
END
ELSE PRINT 'present table dbo.Auth_Session';
GO

IF OBJECT_ID(N'dbo.Auth_Event', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.Auth_Event (
    Auth_Event_ID bigint IDENTITY(1,1) NOT NULL,
    Event_At_Utc datetime2(3) NOT NULL,
    Event_Type varchar(20) NOT NULL,
    Reason varchar(40) NULL,
    Login_Typed nvarchar(100) NULL,
    Login_Key nvarchar(100) NULL,
    User_ID numeric(18,0) NULL,
    Client_IP varchar(45) NULL,
    User_Agent nvarchar(200) NULL,
    Request_Id varchar(36) NULL,
    CONSTRAINT PK_Auth_Event PRIMARY KEY (Auth_Event_ID)
)');
    IF OBJECT_ID(N'dbo.Auth_Event', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.Auth_Event - read the error above';
    ELSE
        PRINT 'created table dbo.Auth_Event';
END
ELSE PRINT 'present table dbo.Auth_Event';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Session') AND name = N'IX_Auth_Session_User')
BEGIN
    EXEC(N'CREATE INDEX IX_Auth_Session_User ON dbo.Auth_Session (User_ID, Expires_Utc)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Session') AND name = N'IX_Auth_Session_User')
        PRINT 'NOT CREATED index dbo.Auth_Session.IX_Auth_Session_User - read the error above';
    ELSE
        PRINT 'created index dbo.Auth_Session.IX_Auth_Session_User';
END
ELSE PRINT 'present index dbo.Auth_Session.IX_Auth_Session_User';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Event') AND name = N'IX_Auth_Event_Login')
BEGIN
    EXEC(N'CREATE INDEX IX_Auth_Event_Login ON dbo.Auth_Event (Login_Key, Event_At_Utc)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Event') AND name = N'IX_Auth_Event_Login')
        PRINT 'NOT CREATED index dbo.Auth_Event.IX_Auth_Event_Login - read the error above';
    ELSE
        PRINT 'created index dbo.Auth_Event.IX_Auth_Event_Login';
END
ELSE PRINT 'present index dbo.Auth_Event.IX_Auth_Event_Login';
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Event') AND name = N'IX_Auth_Event_IP')
BEGIN
    EXEC(N'CREATE INDEX IX_Auth_Event_IP ON dbo.Auth_Event (Client_IP, Event_At_Utc)');
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Event') AND name = N'IX_Auth_Event_IP')
        PRINT 'NOT CREATED index dbo.Auth_Event.IX_Auth_Event_IP - read the error above';
    ELSE
        PRINT 'created index dbo.Auth_Event.IX_Auth_Event_IP';
END
ELSE PRINT 'present index dbo.Auth_Event.IX_Auth_Event_IP';
GO

-- Version stamp

IF OBJECT_ID(N'dbo.alembic_version', N'U') IS NULL
BEGIN
    EXEC(N'CREATE TABLE dbo.alembic_version (version_num varchar(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))');
    IF OBJECT_ID(N'dbo.alembic_version', N'U') IS NULL
        PRINT 'NOT CREATED table dbo.alembic_version - read the error above';
    ELSE
        PRINT 'created table dbo.alembic_version';
END
ELSE PRINT 'present table dbo.alembic_version';
GO
DECLARE @cur varchar(32), @rows int;
SELECT @rows = COUNT(*), @cur = MAX(version_num) FROM dbo.alembic_version;
IF @rows = 1 AND @cur = '0002'
    PRINT 'present version 0002';
ELSE IF @rows = 0 OR (@rows = 1 AND @cur IN ('0001', '0002'))
BEGIN
    DELETE FROM dbo.alembic_version;
    INSERT INTO dbo.alembic_version (version_num) VALUES ('0002');
    PRINT CONCAT('stamped version 0002 (was ', COALESCE(@cur, 'none'), ')');
END
ELSE
    PRINT CONCAT('NOT STAMPED - the database carries ', @rows, ' version row(s), latest ', COALESCE(@cur, 'none'),
                 ', which this script does not know. A newer script may have been run here. Left alone.');
GO

-- App user

DECLARE @login sysname = CAST(SESSION_CONTEXT(N'azztec_app_login') AS sysname);
DECLARE @user sysname, @owner sysname, @sql nvarchar(max), @state varchar(10) = 'refused';
IF COALESCE(@login, N'') = N''
BEGIN
    SET @state = 'skipped';
    PRINT 'skipped app user - @AppLogin is empty';
END
ELSE IF COALESCE(IS_SRVROLEMEMBER(N'sysadmin'), 0) <> 1
    PRINT CONCAT('REFUSED app user - setting up the user for ', @login, ' needs a sysadmin. ',
                 'Run this script again as one.');
ELSE IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = @login)
    PRINT CONCAT('REFUSED app user - login ', @login, ' does not exist on this server. ',
                 'Create the login, then run this script again.');
ELSE IF IS_SRVROLEMEMBER(N'sysadmin', @login) = 1
BEGIN
    SET @state = 'skipped';
    PRINT CONCAT('skipped app user - login ', @login, ' is a sysadmin, which already has every right here ',
                 '(the service should not run as one)');
END
ELSE
BEGIN
    SELECT @user = name FROM sys.database_principals WHERE sid = SUSER_SID(@login);
    SELECT @owner = sp.name
      FROM sys.database_principals dp
      JOIN sys.server_principals sp ON sp.sid = dp.sid
     WHERE dp.name = @login AND dp.type IN ('S', 'U', 'G');
    IF @user = N'dbo'
    BEGIN
        SET @state = 'ok';
        PRINT CONCAT('present user dbo for login ', @login, ' - it owns this database, nothing to grant');
    END
    ELSE IF @user IS NULL AND @owner IS NOT NULL
        PRINT CONCAT('REFUSED app user - user ', @login, ' in this database belongs to login ', @owner,
                     '. Left alone.');
    ELSE
    BEGIN
        IF @user IS NOT NULL
            PRINT CONCAT('present user ', @user, ' for login ', @login);
        ELSE
        BEGIN
            IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = @login AND type IN ('S', 'U', 'G'))
                SET @sql = N'ALTER USER ' + QUOTENAME(@login) + N' WITH LOGIN = ' + QUOTENAME(@login);
            ELSE
                SET @sql = N'CREATE USER ' + QUOTENAME(@login) + N' FOR LOGIN ' + QUOTENAME(@login);
            EXEC sp_executesql @sql;
            SELECT @user = name FROM sys.database_principals WHERE sid = SUSER_SID(@login);
            IF @user IS NULL
                PRINT CONCAT('NOT DONE app user - ', @sql, ' did not take, read the error above');
            ELSE IF @sql LIKE N'ALTER USER%'
                PRINT CONCAT('remapped user ', @user, ' to login ', @login, ' (orphaned by the restore)');
            ELSE
                PRINT CONCAT('created user ', @user, ' for login ', @login);
        END
        IF @user IS NULL
            SET @state = 'failed';
        ELSE
        BEGIN
            SET @state = 'ok';
            IF EXISTS (SELECT 1 FROM sys.database_role_members rm JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id JOIN sys.database_principals m ON m.principal_id = rm.member_principal_id WHERE r.name = N'db_datareader' AND m.name = @user)
                PRINT CONCAT('present db_datareader for ', @user);
            ELSE
            BEGIN
                SET @sql = N'ALTER ROLE db_datareader ADD MEMBER ' + QUOTENAME(@user);
                EXEC sp_executesql @sql;
                IF EXISTS (SELECT 1 FROM sys.database_role_members rm JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id JOIN sys.database_principals m ON m.principal_id = rm.member_principal_id WHERE r.name = N'db_datareader' AND m.name = @user)
                    PRINT CONCAT('granted db_datareader to ', @user);
                ELSE
                BEGIN
                    SET @state = 'failed';
                    PRINT CONCAT('NOT DONE db_datareader for ', @user, ' - read the error above');
                END
            END
            IF EXISTS (SELECT 1 FROM sys.database_role_members rm JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id JOIN sys.database_principals m ON m.principal_id = rm.member_principal_id WHERE r.name = N'db_datawriter' AND m.name = @user)
                PRINT CONCAT('present db_datawriter for ', @user);
            ELSE
            BEGIN
                SET @sql = N'ALTER ROLE db_datawriter ADD MEMBER ' + QUOTENAME(@user);
                EXEC sp_executesql @sql;
                IF EXISTS (SELECT 1 FROM sys.database_role_members rm JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id JOIN sys.database_principals m ON m.principal_id = rm.member_principal_id WHERE r.name = N'db_datawriter' AND m.name = @user)
                    PRINT CONCAT('granted db_datawriter to ', @user);
                ELSE
                BEGIN
                    SET @state = 'failed';
                    PRINT CONCAT('NOT DONE db_datawriter for ', @user, ' - read the error above');
                END
            END
        END
    END
END
EXEC sp_set_session_context @key = N'azztec_app_user', @value = @state;
GO

-- Verify

DECLARE @t int = 0, @c int = 0, @i int = 0, @v varchar(32);
DECLARE @app varchar(10) = CAST(SESSION_CONTEXT(N'azztec_app_user') AS varchar(10));
IF NOT (OBJECT_ID(N'dbo.Action_Header', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Action_Event', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Account_WorkCode', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.External_Contractor', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.WO_N_Plan', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Diag_Log', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Module_Settings', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Diag_NightShift', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Diag_PM_Engine_Run', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Home_View', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Email_Automation', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.PO_Email_Log', N'U') IS NULL) SET @t += 1;
IF NOT (COL_LENGTH(N'dbo.WO_N_Header', N'Source_Action_ID') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.WO_C_header', N'Source_Action_ID') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.Supplier', N'Email_2') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.Supplier', N'Email_3') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.PO_Details', N'Invoice_Ref') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.WO_Attachment', N'Creation_Date') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.WO_Attachment', N'User_id_Created_By') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.WO_M_Attachment', N'Creation_Date') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.WO_M_Attachment', N'User_id_Created_By') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.PO_Attachment', N'Creation_Date') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.PO_Attachment', N'User_id_Created_By') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.Part_Attachment', N'Creation_Date') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.Part_Attachment', N'User_id_Created_By') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.Location_Attachment', N'Creation_Date') IS NULL) SET @c += 1;
IF NOT (COL_LENGTH(N'dbo.Location_Attachment', N'User_id_Created_By') IS NULL) SET @c += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Status_Entry')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Asset')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Promoted')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_RaisedBy')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') AND name = N'IX_Action_Header_Owner')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Event') AND name = N'IX_Action_Event_Action_Date')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Account_WorkCode') AND name = N'UX_Account_WorkCode_Pair')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.External_Contractor') AND name = N'UX_External_Contractor_ShortId')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_Log') AND name = N'IX_Diag_Log_LoggedAt')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_Log') AND name = N'IX_Diag_Log_User_LoggedAt')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_NightShift') AND name = N'IX_Diag_NightShift_Run')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Diag_PM_Engine_Run') AND name = N'IX_Diag_PM_Engine_Run_Started')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Home_View') AND name = N'IX_Home_View_User')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.PO_Email_Log') AND name = N'IX_PO_Email_Log_PO_Id')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.PO_Email_Log') AND name = N'IX_PO_Email_Log_SentDate')) SET @i += 1;
IF NOT (OBJECT_ID(N'dbo.Auth_Session', N'U') IS NULL) SET @t += 1;
IF NOT (OBJECT_ID(N'dbo.Auth_Event', N'U') IS NULL) SET @t += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Session') AND name = N'IX_Auth_Session_User')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Event') AND name = N'IX_Auth_Event_Login')) SET @i += 1;
IF NOT (NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Auth_Event') AND name = N'IX_Auth_Event_IP')) SET @i += 1;
IF OBJECT_ID(N'dbo.alembic_version', N'U') IS NOT NULL
    SELECT @v = MAX(version_num) FROM dbo.alembic_version;
PRINT CONCAT('tables ', @t, '/14  columns ', @c, '/15  indexes ', @i, '/18  version ', COALESCE(@v, 'none'), '  app user ', COALESCE(@app, 'not run'));
IF @t = 14 AND @c = 15 AND @i = 18 AND @v = '0002' AND @app IN ('ok', 'skipped')
    PRINT 'AZZTEC SCHEMA OK';
ELSE
    PRINT 'AZZTEC SCHEMA INCOMPLETE - read the lines above';
GO

SET NOEXEC OFF;
GO
