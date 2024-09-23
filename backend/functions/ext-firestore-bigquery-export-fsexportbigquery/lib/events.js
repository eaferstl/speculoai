"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.recordCompletionEvent = exports.recordSuccessEvent = exports.recordErrorEvent = exports.recordStartEvent = exports.setupEventChannel = void 0;
const eventArc = require("firebase-admin/eventarc");
const { getEventarc } = eventArc;
const EXTENSION_NAME = "firestore-bigquery-export";
const getEventType = (eventName) => `firebase.extensions.${EXTENSION_NAME}.v1.${eventName}`;
let eventChannel;
/** setup events */
const setupEventChannel = () => {
    eventChannel =
        process.env.EVENTARC_CHANNEL &&
            getEventarc().channel(process.env.EVENTARC_CHANNEL, {
                allowedEventTypes: process.env.EXT_SELECTED_EVENTS,
            });
};
exports.setupEventChannel = setupEventChannel;
const recordStartEvent = async (data) => {
    if (!eventChannel)
        return;
    return eventChannel.publish({
        type: getEventType("onStart"),
        data,
    });
};
exports.recordStartEvent = recordStartEvent;
const recordErrorEvent = async (err, subject) => {
    if (!eventChannel)
        return;
    return eventChannel.publish({
        type: getEventType("onError"),
        data: { message: err.message },
        subject,
    });
};
exports.recordErrorEvent = recordErrorEvent;
const recordSuccessEvent = async ({ subject, data, }) => {
    if (!eventChannel)
        return;
    return eventChannel.publish({
        type: getEventType("onSuccess"),
        subject,
        data,
    });
};
exports.recordSuccessEvent = recordSuccessEvent;
const recordCompletionEvent = async (data) => {
    if (!eventChannel)
        return;
    return eventChannel.publish({
        type: getEventType("onCompletion"),
        data,
    });
};
exports.recordCompletionEvent = recordCompletionEvent;
