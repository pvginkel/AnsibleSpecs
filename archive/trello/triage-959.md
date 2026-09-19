# Revert RDP feature-flag workaround on WRKDEVWIN once Microsoft fixes the September 2026 RDP deadlock

## 📋 List: Operator Actions

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `black_dark` Solution Known
- `yellow` Chore

## 📅 Due Date: ⏰ Due 10/16/2026, 9:00:00 AM

## 👥 Members

_None_

## 📝 Description

**Context**
WRKDEVWIN (Windows 11 Pro 25H2, Proxmox VM) hung twice on 10 and 11 Sep 2026: RDP reconnect stuck at "connecting", console logon spinning, shutdown never completing, only a PVE reset recovered it. Cause: Remote Desktop session-teardown deadlock (RDPSERVERBASE!WDLIB_Close, audio-redirection code path, feature flag 3802373433) introduced by the 8 Sep 2026 cumulative update KB5124008 (rdpserverbase.dll 10.0.26100.9444). Fingerprint in the log: TerminalServices-RemoteConnectionManager/Admin events 20498 + 20502.

**Workaround applied on 11 Sep 2026 17:27** (community workaround, unofficial):
- Registry key `HKLM\SYSTEM\CurrentControlSet\Control\FeatureManagement\Overrides\4\3802373433` with `EnabledState`=1 and `EnabledStateOptions`=0 (DWORD)
- TermService restarted
- Backup of the Overrides key saved before the change (FeatureOverrides-backup-20260911-172729.reg in the session temp folder; re-export is trivial, the only change is this one subkey)

**When to revert**
Once Microsoft ships a fix for the RDP teardown deadlock (check the KB notes of the October 2026 cumulative update and the Windows 11 25H2 release-health page, https://learn.microsoft.com/en-us/windows/release-health/status-windows-11-25h2) and that update is installed on WRKDEVWIN.

**How to revert** (elevated PowerShell):
```
Remove-Item -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FeatureManagement\Overrides\4\3802373433" -Force
Restart-Service -Name TermService -Force
```
Then verify over the following days that RDP reconnects and shutdowns still work, and that no new 20498/20502 events appear in TerminalServices-RemoteConnectionManager/Admin.

**References**
- https://www.bleepingcomputer.com/news/microsoft/september-windows-server-updates-break-remote-desktop-services/
- https://lazyadmin.nl/it/september-2026-update-break-rds-how-to-fix/
- https://support.microsoft.com/help/5124008

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/13/2026, 10:26:54 AM
Closed 13 Sep 2026. The feature-flag override did NOT prevent the hang: WRKDEVWIN deadlocked a third time on 13 Sep (RDP service already wedged since the session disconnect on Fri 11 Sep 22:21; hard reset 10:01). Microsoft confirmed the issue for Windows 11 24H2/25H2 on 11 Sep with no fix yet.

Action taken instead (13 Sep, ~10:40):
- Override key HKLM\SYSTEM\CurrentControlSet\Control\FeatureManagement\Overrides\4\3802373433 removed (verified gone).
- KB5124008 (LCU 26200.9445) removed via DISM; machine is back on build 26200.9168 (August LCU KB5121003), rdpserverbase.dll 10.0.26100.8972.
- Windows Update paused until 2026-10-18T08:40Z so the September LCU is not reinstalled.

Nothing left to revert. Updates resume automatically on 18 Oct 2026, after the 13 Oct Patch Tuesday; check that the October cumulative update's notes list the RDS fix before letting it install. Release health: https://learn.microsoft.com/en-us/windows/release-health/status-windows-11-25h2

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/Z1vphEJA/959-revert-rdp-feature-flag-workaround-on-wrkdevwin-once-microsoft-fixes-the-september-2026-rdp-deadlock
- **Short URL**: https://trello.com/c/Z1vphEJA

---
*Last Activity: 9/13/2026, 10:26:57 AM*
*Card ID: 6aa41e45dbe6889376a37c54*
