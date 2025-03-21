// routes.js
module.exports = (server) => {
  // ダッシュボード関連
  server.get('/api/v1/dashboard/summary', (req, res) => {
    const db = server.db.getState();
    res.jsonp(db.dashboard);
  });

  server.get('/api/v1/dashboard/process-status', (req, res) => {
    const db = server.db.getState();
    res.jsonp(db.dashboard);
  });

  server.get('/api/v1/dashboard/activity', (req, res) => {
    const db = server.db.getState();
    res.jsonp(db.dashboard);
  });

  server.get('/api/v1/dashboard/alerts', (req, res) => {
    const db = server.db.getState();
    res.jsonp(db.dashboard);
  });

  // エージェント関連
  server.get('/api/v1/agents', (req, res) => {
    const db = server.db.getState();
    res.jsonp(db.agents);
  });

  server.get('/api/v1/agents/message-flow', (req, res) => {
    const db = server.db.getState();
    res.jsonp(db.agentFlow);
  });

  server.get('/api/v1/agents/:id', (req, res) => {
    const db = server.db.getState();
    const agent = db.agents.find(a => a.id === req.params.id);
    if (agent) {
      res.jsonp(agent);
    } else {
      res.status(404).jsonp({ error: 'Agent not found' });
    }
  });

  // 他のエンドポイントも同様に定義...
  // 例として主要なものだけ実装
} 