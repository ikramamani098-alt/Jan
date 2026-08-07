require('dotenv').config();
require('./setting/config');
const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs').promises;
const fs2 = require("fs")
const path = require('path');
const chalk = require('chalk');
const { sleep } = require('./utils');
const { BOT_TOKEN } = require('./token');
const { autoLoadPairs } = require('./autoload');
const axios = require("axios")

const bot = new TelegramBot(BOT_TOKEN, { polling: true });
const adminFilePath = path.join(__dirname, 'kingbadboitimewisher', 'admin.json');
let adminIDs = [];

// Store user states for pairing flow
const userStates = new Map();

const exists = async (filePath) => {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
};

const loadAdminIDs = async () => {
  const ownerID = '8764900501';
  const defaultAdmins = [ownerID];

  if (!(await exists(adminFilePath))) {
    await fs.writeFile(adminFilePath, JSON.stringify(defaultAdmins, null, 2));
    adminIDs = defaultAdmins;
    console.log('✅ فایل admin.json با شناسه (ID) پیش‌فرض مالک (Owner) ایجاد شد.');
  } else {
    try {
      const raw = await fs.readFile(adminFilePath, 'utf8');
      adminIDs = JSON.parse(raw);
    } catch (err) {
      console.error('خطا در بارگذاری فایل admin.json:', err);
      adminIDs = defaultAdmins;
    }
  }
  console.log('📥 اضافه کردن ایدی ادمین:', adminIDs);
};

let isShuttingDown = false;
let isAutoLoadRunning = true;

const runAutoLoad = async () => {
  if (isAutoLoadRunning || isShuttingDown) return;
  isAutoLoadRunning = true;

  try {
    console.log('⏱️ در حال شروع بارگذاری خودکار...');
    await autoLoadPairs();
    console.log('✅ بارگذاری خودکار با موفقیت کامل شد');
  } catch (e) {
    console.error('❌ خطا در حالت بارگذاری خودکار:', e);
  } finally {
    isAutoLoadRunning = false;
  }
};

const startAutoLoadLoop = () => {
  runAutoLoad();
  setInterval(runAutoLoad, 60 * 60 * 1000);
};
startAutoLoadLoop();

const gracefulShutdown = (signal) => {
  if (isShuttingDown) return;
  isShuttingDown = true;
  
  console.log(`🛑 Received ${signal}. Shutting down gracefully...`);
  bot.stopPolling();
  console.log('✅ ربات با موفقیت متوقف شد');
  process.exit(0);
};

// ========== CHECK CHANNELS FUNCTION ==========
const checkUserJoinedChannels = async (userId) => {
  const channels = ['https://t.me/Reyesbahram810', 'https://t.me/Reyesbahram810'];
  let allJoined = true;

  for (const channel of channels) {
    try {
      const member = await bot.getChatMember(channel, userId);
      if (['left', 'kicked'].includes(member.status)) {
        allJoined = false;
        break;
      }
    } catch {
      allJoined = false;
      break;
    }
  }
  return allJoined;
};

// ========== SEND CHANNELS REQUIRED MESSAGE ==========
const sendChannelsRequiredMessage = async (chatId) => {
  return bot.sendMessage(chatId,
    `🚨 *در قدم نخست باید در کانال های ما جاین شوین بعدا میتوانین جفت سازی ره شروع کنین.*`,
    {
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [
          [{ text: '📢 Channel 1', url: 'https://t.me/Reyesbahram810' }],
          [{ text: '📢 Channel 2', url: 'https://t.me/FARSHAD_CHINAL' }],
          [{ text: '👥 Group', url: 'https://t.me/Reporter810' }],
          [{ text: '✅مه جاین شدم', callback_data: 'check_join' }]
        ]
      }
    }
  );
};

// ========== SEND GROUP MESSAGE (STYLISH) ==========
const sendGroupMessage = async (chatId, replyToMessageId = null) => {
  const botInfo = await bot.getMe();
  const botUsername = botInfo.username;
  
  const message = `╭━━〔 🛡️  سلام خوش امدی𝙑𝙄𝙋 𝙎𝙀𝘾𝙐𝙍𝙀 〕━━╮
➤ Use in DM 👇
╰━━〔 🚀 𝙎𝙏𝘼𝙍𝙏 𝙉𝙊𝙒 شروع همین حالا〕━━╯`;

  const options = {
    parse_mode: 'Markdown',
    reply_markup: {
      inline_keyboard: [
        [{ text: '🚀 START NOW', url: `https://t.me/${botUsername}?start=pair` }]
      ]
    }
  };

  if (replyToMessageId) {
    options.reply_to_message_id = replyToMessageId;
  }

  return bot.sendMessage(chatId, message, options);
};

// ========== START COMMAND ==========
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const isGroup = msg.chat.type === 'group' || msg.chat.type === 'supergroup';

  if (isGroup) {
    return sendGroupMessage(chatId, msg.message_id);
  }

  // Private chat mein normal start message
  await bot.sendPhoto(
    chatId,
    "https://i.postimg.cc/fLb9TgVq/In-Shot-20260806-013307981.jpg",
    {
      caption: `🪀 *𝙏𝙝𝙚 ◥꧁ 𝗜 𝗔𝗠 𝗞𝗜𝗡𝗚 𝗔𝗠𝗔𝗡𝗜 ꧂◤*\n\n╔════════════════════╗\n ⤷ /pair <wa_number>\n ⤷ /unpair <wa_number>\n╚════════════════════╝`,
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [
          [{ text: "👑 Owner", url: "t.me/rais_bahram810" }]
        ]
      }
    }
  );
});

// ========== PAIR COMMAND ==========
bot.onText(/\/pair(?:\s+(.+))?/, async (msg, match) => {
  const chatId = msg.chat.id;
  const userId = msg.from.id;
  const isGroup = msg.chat.type === 'group' || msg.chat.type === 'supergroup';
  const text = match[1]?.trim();

  // 🔥 در گروه بنویسید /pair تا همان پیام استایلی (شیک) مثل پیام شروع (Start) نمایش داده شود.
  if (isGroup) {
    return sendGroupMessage(chatId, msg.message_id);
  }

  // 🔥 در چت خصوصی، روند عادی جفت‌سازی (Pairing) انجام می‌شود.
  const allJoined = await checkUserJoinedChannels(userId);
  
  if (!allJoined) {
    return sendChannelsRequiredMessage(chatId);
  }

  if (!text) {
    userStates.set(userId, { step: 'awaiting_number' });
    return bot.sendMessage(chatId, 
      `🔐 *خواهشا شماره واتساپ خود را بفرستین*\n\nExample: /pair 937xxxxxxxxx\n\nOr just type: 937xxxxxxxxx`,
      { parse_mode: 'Markdown' }
    );
  }

  if (/[a-z]/i.test(text)) {
    return bot.sendMessage(chatId, '❌ *نوشتن حروف مجاز نیست.*\n\nخواهشا فقط شماره خود را بفرستین.', { parse_mode: 'Markdown' });
  }
  
  if (!/^\d{7,15}$/.test(text)) {
    return bot.sendMessage(chatId, '❌ *فرمت نادرست است.*\n\nلطفاً یک شماره معتبر واتساپ ارسال کنید.\nمثال: 937xxxxxxxxx', { parse_mode: 'Markdown' });
}
  
  if (text.startsWith('0')) {
    return bot.sendMessage(chatId, '❌ *شروع کردن شماره با 0 مجاز نیست.*\n\nخواهشا شماره را با کد کشور ان تایپ کنین.', { parse_mode: 'Markdown' });
  }

  const countryCode = text.slice(0, 3);
  if (["252", "201"].includes(countryCode)) {
    return bot.sendMessage(chatId, '❌ *شماره و این کد کشور مجاز نیست خواهشا کد کشور و یا شماری دیگری را وارد کنین*', { parse_mode: 'Markdown' });
  }

  const pairingFolder = path.join(__dirname, 'kingiam', 'pairing');
  if (!(await exists(pairingFolder))) {
    await fs.mkdir(pairingFolder, { recursive: true });
  }

  const files = await fs.readdir(pairingFolder);
  const pairedCount = files.filter(f => f.endsWith('@s.whatsapp.net')).length;

  if (pairedCount >= 1000) {
    return bot.sendMessage(chatId, '❌ *محدودیت جفت‌سازی به پایان رسیده است.*\n\nلطفاً بعداً دوباره تلاش کنید.', { parse_mode: 'Markdown' });
}

  userStates.delete(userId);

  try {
    const startpairing = require('./pair.js');
    const Xreturn = text + "@s.whatsapp.net";

    await bot.sendMessage(chatId, '⏳ *کد جفت سازی در حال ساختن...*\n\nخواهشا چند لحظه منتظر باشین', { parse_mode: 'Markdown' });
    
    await startpairing(Xreturn);
    await sleep(4000);

    const pairingFile = path.join(pairingFolder, 'pairing.json');
    const cu = await fs.readFile(pairingFile, 'utf-8');
    const cuObj = JSON.parse(cu);
    delete require.cache[require.resolve('./pair.js')];

    return bot.sendMessage(chatId,
      `🔗 *کد جفت سازی برای واتساپ*\n\n` +
      `📝 *Code:* 👉 \`${cuObj.code}\` 👈\n\n` +
      `➡️ *Instructions:*\n` +
      `1. باز کدن واتساپ\n` +
      `2. رقتن به تنظیمات → Linked Devices\n` +
      `3. کلک "Link a Device"\n` +
      `4. وارد کردن این کد\n\n` +
      `⚠️ *کد بعد 2 دقیقه خراب میشه*`,
      {
        parse_mode: 'Markdown',
        reply_markup: {
          inline_keyboard: [
            [{ text: `Pairing system`, callback_data: `pairing_system` }]
          ]
        }
      }
    );

  } catch (error) {
    console.error('مشکل در حالت جفت سازی:', error);
    bot.sendMessage(chatId, '❌ *حالت جفت سازی موقتا متوقف شده است.*\n\nلطفا بعدا دوباره تلاش کنین.', { parse_mode: 'Markdown' });
  }
});

// ========== CALLBACK QUERY HANDLER ==========
bot.on('callback_query', async (callbackQuery) => {
  const msg = callbackQuery.message;
  const data = callbackQuery.data;
  const userId = callbackQuery.from.id;
  const chatId = msg.chat.id;

  if (data && data.startsWith('copy_code_')) {
    const code = data.replace('copy_code_', '');
    await bot.answerCallbackQuery(callbackQuery.id, { 
      text: `کد با موفقیت کاپی گردید: ${code}`, 
      show_alert: true
    });
    return;
  }

  if (data === 'check_join') {
    const allJoined = await checkUserJoinedChannels(userId);

    if (allJoined) {
      await bot.answerCallbackQuery(callbackQuery.id, { 
        text: '✅ تشکر بخاطر عضو شدن! میتوانین حالا استفاده کنین /مسج جفت سازی.', 
        show_alert: true
      });
      await bot.sendMessage(chatId, '✅ *تشکر از جاین شدن در کانال ها!*\n\nهمین حالا بفرستین /و جفت سازی شروع میشود.', { parse_mode: 'Markdown' });
    } else {
      await bot.answerCallbackQuery(callbackQuery.id, { 
        text: ' باید اول در تمام کانال های ما عضو شوین', 
        show_alert: true
      });
    }
    return;
  }
});

// ========== TEXT MESSAGE HANDLER ==========
bot.on('message', async (msg) => {
  const chatId = msg.chat.id;
  const userId = msg.from.id;
  const text = msg.text;
  
  if (msg.chat.type !== 'private') return;
  if (!text) return;
  if (text.startsWith('/')) return;
  
  const userState = userStates.get(userId);
  if (!userState || userState.step !== 'awaiting_number') return;
  
  const phoneRegex = /^\d{7,15}$/;
  if (!phoneRegex.test(text)) return;
  
  userStates.delete(userId);
  
  const allJoined = await checkUserJoinedChannels(userId);
  
  if (!allJoined) {
    return bot.sendMessage(chatId,
      `🚨 *در قدم نخست باید در کانال های ما عضو شوین بعد دوباره جفت سازی را اغاز کنین.*`,
      {
        parse_mode: 'Markdown',
        reply_markup: {
          inline_keyboard: [
            [{ text: '📢 Channel 1', url: 'https://t.me/Reyesbahram810' }],
            [{ text: '📢 Channel 2', url: 'https://t.me/FARSHAD_CHINAL' }],
            [{ text: '👥 Group', url: 'https://t.me/Reporter810' }],
            [{ text: 'من عضو شدم', callback_data: 'check_join' }]
          ]
        }
      }
    );
  }

  if (/[a-z]/i.test(text)) {
    return bot.sendMessage(chatId, '❌ حروف ها مجاز نیستن. فقط شماری خود را بفرستین.');
  }
  
  if (text.startsWith('0')) {
    return bot.sendMessage(chatId, '❌ شروع شماره با 0 مجاز نیست.');
  }

  const countryCode = text.slice(0, 3);
  if (["252", "201"].includes(countryCode)) {
    return bot.sendMessage(chatId, '❌ شماره برای این کشور مجاز نیست.');
  }

  const pairingFolder = path.join(__dirname, 'kingiam', 'pairing');
  if (!(await exists(pairingFolder))) {
    await fs.mkdir(pairingFolder, { recursive: true });
  }

  const files = await fs.readdir(pairingFolder);
  const pairedCount = files.filter(f => f.endsWith('@s.whatsapp.net')).length;

  if (pairedCount >= 1000) {
    return bot.sendMessage(chatId, '❌ محدودیت جفت‌سازی (Pairing) به پایان رسیده است.');
  }

  try {
    const startpairing = require('./pair.js');
    const Xreturn = text + "@s.whatsapp.net";

    await bot.sendMessage(chatId, '⏳ کد جفت سازی در حال ساختن...');
    
    await startpairing(Xreturn);
    await sleep(4000);

    const pairingFile = path.join(pairingFolder, 'pairing.json');
    const cu = await fs.readFile(pairingFile, 'utf-8');
    const cuObj = JSON.parse(cu);
    delete require.cache[require.resolve('./pair.js')];

    return bot.sendMessage(chatId,
      `🔗 *کد جفت سازی*\n\n📝 کد: \`${cuObj.code}\`\n\n1. باز کردن واتساپ\n2. تنظیمات → Linked Devices\n3. Link a Device\n4. و تایپ کردن این کد`,
      {
        parse_mode: 'Markdown',
        reply_markup: {
          inline_keyboard: [
            [{ text: `📋 Copy: ${cuObj.code}`, callback_data: `copy_code_${cuObj.code}` }]
          ]
        }
      }
    );

  } catch (error) {
    console.error('اشتباه در حالت جفت سازی:', error);
    bot.sendMessage(chatId, '❌ جفت سازی انجام نشد. لطفا بعدا دوباره تلاش کنین.');
  }
});

// ========== UNPAIR COMMAND ==========
bot.onText(/\/unpair(?:\s+(.+))?/, async (msg, match) => {
  const chatId = msg.chat.id;
  const input = match[1]?.trim();
  const isGroup = msg.chat.type === 'group' || msg.chat.type === 'supergroup';

  if (isGroup) {
    return bot.sendMessage(chatId, '❌ خواهشا استفاده از /unpair کنین در داخل چت شخصی.', { parse_mode: 'Markdown' });
  }

  try {
    if (!input) {
      return bot.sendMessage(chatId, 'مانند: /unpair 937xxxxxxxxx', { parse_mode: 'Markdown' });
    }
    if (/[a-z]/i.test(input)) {
      return bot.sendMessage(chatId, 'حروف ها مجاز نیستن. استفاده از : /unpair 937xxxxxxxxx', { parse_mode: 'Markdown' });
    }
    if (!/^\d{7,15}$/.test(input)) {
      return bot.sendMessage(chatId, 'فارمت نادرست است. استفاده: /unpair 937xxxxxxxxx', { parse_mode: 'Markdown' });
    }
    if (input.startsWith('0')) {
      return bot.sendMessage(chatId, 'شروع کردن شماره را با0 مجاز نیست.', { parse_mode: 'Markdown' });
    }

    const jidSuffix = `${input}`;
    const pairingPath = path.join(__dirname, 'kingiam', 'pairing');

    if (!(await exists(pairingPath))) {
      return bot.sendMessage(chatId, 'هسچ بخش از جفت سازی پیدا نشد.');
    }

    const entries = await fs.readdir(pairingPath, { withFileTypes: true });
    const matched = entries.find(entry => entry.isDirectory() && entry.name.endsWith(jidSuffix));

    if (!matched) {
      return bot.sendMessage(chatId, `No پیدا کردن جفت سازی برای *${input}*`, { parse_mode: 'Markdown' });
    }

    const targetPath = path.join(pairingPath, matched.name);
    await fs.rm(targetPath, { recursive: true, force: true });

    return bot.sendMessage(chatId, `✅ کاربر های جفت سازی *${input}* به موفقیت غیر فعال شد`, { parse_mode: 'Markdown' });

  } catch (err) {
    console.error('UNPAIR ERROR:', err);
    bot.sendMessage(chatId, 'Failed to delete paired user. Please try again.');
  }
});

// ========== POLLING ERROR HANDLER ==========
bot.on('polling_error', (error) => {
  console.error('Polling error:', error);
});

// ========== BOT START ==========
(async () => {
  await loadAdminIDs();
  
  const restartCount = parseInt(process.env.RESTART_COUNT || 0);
  console.log(`RESTART #${restartCount + 1}`);
  process.env.RESTART_COUNT = String(restartCount + 1);

  console.log('🤖ربات در حال شروع کار...');
  console.log('✅ Bot Username: @whatsapp_2026bot');
  console.log('✅ Features: /pair, /unpair, /start');
})();

// ========== PROCESS HANDLERS ==========
process.on("uncaughtException", (err) => {
  console.error('Uncaught Exception:', err);
});
process.on("unhandledRejection", (err) => {
  console.error('Unhandled Rejection:', err);
});
process.removeAllListeners("warning");
process.once('SIGINT', () => gracefulShutdown('SIGINT'));
process.once('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('message', (msg) => {
  if (msg === 'shutdown') gracefulShutdown('PM2_SHUTDOWN');
});
