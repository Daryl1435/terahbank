import 'react-native-get-random-values'; // must be first — polyfills crypto.getRandomValues for uuid
import { registerRootComponent } from 'expo';
import App from './App';

registerRootComponent(App);
