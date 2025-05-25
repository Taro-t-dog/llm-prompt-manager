# 🚀 LLM Prompt Manager

Git風のバージョン管理でLLMプロンプトの管理、評価、最適化を行う統合システム

## 機能

- **🤖 プロンプト実行**: Google Geminiモデルを使用したプロンプト実行とコスト追跡
- **🌿 バージョン管理**: プロンプト開発ワークフロー用のGit風ブランチ管理
- **📊 自動評価**: カスタム基準に基づくAI駆動の評価システム
- **💰 コスト分析**: リアルタイムトークン計算とコスト算出
- **🔍 比較ツール**: プロンプト結果の差分可視化機能付き並列比較
- **📁 データ管理**: チーム連携用のエクスポート・インポート機能

## クイックスタート

### 必要環境
- Python 3.8以上
- Google AI Studio APIキー

### インストール

```bash
git clone https://github.com/yourusername/llm-prompt-manager.git
cd llm-prompt-manager
pip install -r requirements.txt
streamlit run app.py
```

### 初期設定
1. サイドバーでGemini APIキーを入力
2. プロンプト実行開始

## 使い方

### 基本ワークフロー

1. **実行タブ**: プロンプトの作成と実行
   - テンプレートモード: `{user_input}`で動的データを使用
   - 単一モード: 直接プロンプトを実行
   - カスタム評価基準の設定

2. **履歴タブ**: 実行履歴の閲覧
   - モデル、ブランチ、内容での検索・フィルタリング
   - 各実行の詳細表示

3. **比較タブ**: 2つの実行結果を比較
   - 文字レベルの差分可視化
   - コストとパフォーマンス指標
   - 結果の並列比較

4. **分析タブ**: プロジェクト概要
   - ブランチ構造の可視化
   - 使用統計とコスト情報




## ファイル構造

```
llm-prompt-manager/
├── app.py                    # メインStreamlitアプリケーション
├── config/
│   ├── __init__.py
│   └── models.py            # モデル設定と料金情報
├── core/
│   ├── __init__.py
│   ├── evaluator.py         # Gemini API統合
│   ├── git_manager.py       # バージョン管理ロジック
│   └── data_manager.py      # データインポート・エクスポート
├── ui/
│   ├── __init__.py
│   ├── styles.py            # CSSスタイリング
│   ├── components.py        # 再利用可能UIコンポーネント
│   └── tabs/                # タブ実装
│       ├── execution_tab.py
│       ├── history_tab.py
│       ├── comparison_tab.py
│       └── visualization_tab.py
└── requirements.txt
```

## 設定

### 対応モデル

| モデル | 入力コスト | 出力コスト | 特徴 |
|-------|------------|-------------|----------|
| Gemini 2.0 Flash | $0.10/1Mトークン | $0.40/1Mトークン | 高性能 |


### データエクスポート・インポート

- **JSON**: ブランチとメタデータを含む完全バックアップ
- **CSV**: 外部分析用の実行データ

## 開発

### 主要クラス

- `GeminiEvaluator`: API呼び出しとコスト計算を処理
- `GitManager`: ブランチ、コミット、バージョン履歴を管理
- `DataManager`: データの永続化と共有を処理

### 新機能の追加

1. リポジトリをフォーク
2. 機能ブランチを作成
3. 既存パターンに従って変更を実装
4. プルリクエストを提出

## トラブルシューティング

### よくある問題

**APIキーエラー**: Google AI Studioでキーを確認してください
**インポートエラー**: `pip install -r requirements.txt`で全依存関係がインストールされていることを確認
**パフォーマンス問題**: ブラウザキャッシュをクリアするか、履歴サイズを削減してください

## ライセンス

MIT License - 詳細はLICENSEファイルを参照

## 貢献

貢献を歓迎します！プルリクエストを提出する前に貢献ガイドラインをお読みください。

1. GitHub Issuesでバグ報告と機能要求
2. GitHub Discussionsで質問とコミュニティサポート
3. プルリクエストでコード改善を提出

## サポート

- GitHub Issues: バグ報告と機能要求
- GitHub Discussions: 質問とコミュニティサポート