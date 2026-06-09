# Troubleshooting

| Problem | Solution |
|---------|----------|
| Upload returns `404` | Restart backend after code changes |
| `Run Analysis` shows no change | Alerts deduplicated — load fresh sample data |
| No terminal logs | Check `data/runtime/server.log` |
| Webhook not received | Run `python scripts/mock_webhook.py` |
| AI analysis fails | Verify `AZURE_OPENAI_*` in `.env`, deployment `gpt-4.1` |
| Port 8000 in use | Kill orphaned uvicorn Python processes |
| Wrong file uploaded | Use `data/incoming/sample-app.log` |
| Dashboard empty | Load sample data → Run Analysis |

## Kill orphaned uvicorn (Windows)

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'uvicorn' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```
