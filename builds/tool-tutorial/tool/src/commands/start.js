import createLogger from '../logger.js';
const logger = createLogger('my-tool');

export default function start(config) {
    logger.highlight(' Starting the app ');
    logger.debug('Received configuration in start - ', config);
}
