#!/usr/bin/env node

/**
 * Anthropic API 问答测试脚本
 * 使用方法: node test-api.js "你的问题"
 */

const API_KEY = "";
const BASE_URL = "https://open.bigmodel.cn/api/anthropic";
const MODEL = "glm-4.7";

async function chat(question) {
    try {
        const response = await fetch(`${BASE_URL}/v1/messages`, {
            method: "POST",
            headers: {
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            body: JSON.stringify({
                model: MODEL,
                max_tokens: 2048,
                messages: [
                    {
                        role: "user",
                        content: question,
                    },
                ],
            }),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API 错误: ${response.status} - ${error}`);
        }

        const data = await response.json();
        return data.content[0].text;
    } catch (error) {
        console.error("❌ 请求失败:", error.message);
        throw error;
    }
}

// 交互式问答模式
async function interactiveMode() {
    console.log("🤖 Anthropic API 问答测试");
    console.log('输入 "exit" 或 "quit" 退出\n');
    console.log(`📡 使用模型: ${MODEL}`);
    console.log(`🌐 API 端点: ${BASE_URL}\n`);

    const readline = require("readline");
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });

    const askQuestion = (query) => {
        return new Promise((resolve) => rl.question(query, resolve));
    };

    try {
        while (true) {
            const question = await askQuestion("❓ 你的问题: ");

            if (question.toLowerCase() === "exit" || question.toLowerCase() === "quit") {
                console.log("👋 再见!");
                rl.close();
                break;
            }

            if (!question.trim()) {
                console.log("⚠️  请输入一个问题\n");
                continue;
            }

            console.log("🤔 思考中...");
            try {
                const answer = await chat(question);
                console.log(`\n💡 回答:\n${answer}\n`);
            } catch (error) {
                console.log(`\n❌ 错误: ${error.message}\n`);
            }
        }
    } catch (error) {
        console.error("❌ 程序错误:", error);
        rl.close();
    }
}

// 命令行模式
async function main() {
    const args = process.argv.slice(2);

    if (args.length === 0) {
        // 交互式模式
        await interactiveMode();
    } else {
        // 单次问答模式
        const question = args.join(" ");
        console.log(`❓ 问题: ${question}\n`);
        console.log("🤔 思考中...");

        try {
            const answer = await chat(question);
            console.log(`\n💡 回答:\n${answer}`);
        } catch (error) {
            console.error(`\n❌ 错误: ${error.message}`);
            process.exit(1);
        }
    }
}

main();
