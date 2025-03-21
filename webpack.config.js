const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const webpack = require('webpack');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';
  const useMockApi = process.env.REACT_APP_USE_MOCK_API === 'true';

  return {
    entry: './src/index.js',
    output: {
      filename: 'bundle.js',
      path: path.resolve(__dirname, 'dist'),
    },
    module: {
      rules: [
        {
          test: /\.(js|jsx)$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: ['@babel/preset-env', '@babel/preset-react'],
            },
          },
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
        {
          test: /\.(png|svg|jpg|jpeg|gif)$/i,
          type: 'asset/resource',
        },
      ],
    },
    resolve: {
      extensions: ['.js', '.jsx'],
    },
    devServer: {
      static: {
        directory: path.join(__dirname, 'public'),
      },
      historyApiFallback: true,
      hot: true,
      port: 3001,
      proxy: {
        '/api': {
          target: 'http://localhost:3002', // バックエンドのURLを指定
          changeOrigin: true,
          secure: false,
          headers: {
            Connection: 'keep-alive'
          }
        }
      }
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: './public/index.html',
      }),
      new webpack.DefinePlugin({
        'process.env.NODE_ENV': JSON.stringify(isProduction ? 'production' : 'development'),
        'process.env.REACT_APP_USE_MOCK_API': JSON.stringify(useMockApi ? 'true' : 'false')
      }),
    ],
  };
}; 