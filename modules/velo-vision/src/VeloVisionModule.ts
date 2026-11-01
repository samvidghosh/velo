import { NativeModule, requireNativeModule } from 'expo';

declare class VeloVisionModule extends NativeModule<{}> {
  analyzeVideo(uri: string): Promise<string>;
}

export default requireNativeModule<VeloVisionModule>('VeloVision');
