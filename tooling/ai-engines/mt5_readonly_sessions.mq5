// Read-only session export. No trading, login, subscription, or account changes.
#property script_show_inputs
input string OutputFile = "FTMO_READONLY_SESSIONS.json";

string Escape(string s) {
   StringReplace(s,"\\","\\\\"); StringReplace(s,"\"","\\\"");
   return s;
}

string Sessions(string symbol, bool trade) {
   string out="["; bool first=true;
   for(int day=0; day<7; day++) {
      for(uint i=0; i<32; i++) {
         datetime from=0,to=0;
         bool ok=trade ? SymbolInfoSessionTrade(symbol,(ENUM_DAY_OF_WEEK)day,i,from,to)
                       : SymbolInfoSessionQuote(symbol,(ENUM_DAY_OF_WEEK)day,i,from,to);
         if(!ok) break;
         if(!first) out+=","; first=false;
         out+=StringFormat("{\"weekday\":%d,\"index\":%d,\"from_server_seconds\":%I64d,\"to_server_seconds\":%I64d}",day,i,(long)from,(long)to);
      }
   }
   return out+"]";
}

void OnStart() {
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO) {
      Print("Stopped: DEMO account required."); return;
   }
   string server=AccountInfoString(ACCOUNT_SERVER);
   string upper=server; StringToUpper(upper);
   if(StringFind(upper,"FTMO")<0) { Print("Stopped: FTMO server required."); return; }
   string names[]={"XAUUSD","EURUSD","US500","GBPUSD","AUDUSD"};
   string out=StringFormat("{\"schema\":\"mt5-readonly-sessions-v1\",\"login\":%I64d,\"server\":\"%s\",\"observed_server_time\":%I64d,\"symbols\":{",
      AccountInfoInteger(ACCOUNT_LOGIN),Escape(server),(long)TimeTradeServer());
   for(int i=0;i<ArraySize(names);i++) {
      if(i>0) out+=",";
      out+="\""+names[i]+"\":{\"sessions_quote\":"+Sessions(names[i],false)+",\"sessions_trade\":"+Sessions(names[i],true)+"}";
   }
   out+="}}";
   int handle=FileOpen(OutputFile,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
   if(handle==INVALID_HANDLE) { Print("Cannot write private session export."); return; }
   FileWriteString(handle,out); FileClose(handle);
   Print("Saved read-only session export under terminal MQL5/Files. Keep private.");
}
